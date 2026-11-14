# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
import pytest
from fastapi.testclient import TestClient

# Set SANDBOX_DIR before importing app to avoid initialization issues
os.environ["SANDBOX_DIR"] = "/tmp/sandbox_test"
os.makedirs("/tmp/sandbox_test", exist_ok=True)

from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_sandbox_dir(tmp_path, monkeypatch):
    sandbox_dir = str(tmp_path)
    monkeypatch.setenv("SANDBOX_DIR", sandbox_dir)
    import app.main
    monkeypatch.setattr(app.main, "SANDBOX_DIR", sandbox_dir)
    return sandbox_dir

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Sandbox Runtime is active."}

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Sandbox Runtime is active."}

def test_execute_command(setup_sandbox_dir):
    response = client.post("/execute", json={"command": "echo 'hello world'"})
    assert response.status_code == 200
    data = response.json()
    assert "hello world" in data["stdout"]
    assert data["exit_code"] == 0


def test_execute_async_command_success(setup_sandbox_dir):
    start_response = client.post(
        "/execute/start",
        json={
            "command": "python3 -c \"import os, time; time.sleep(0.05); print(os.getcwd()); print('async hello')\""
        },
    )
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "running"
    job_id = start_data["job_id"]
    assert isinstance(job_id, str) and len(job_id) > 0

    status_data = None
    for _ in range(50):
        status_response = client.get(f"/execute/status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["job_id"] == job_id
        if status_data["status"] == "completed":
            break
        assert status_data["status"] == "running"
        assert status_data["exit_code"] is None
        time.sleep(0.02)

    assert status_data is not None
    assert status_data["status"] == "completed"
    assert os.path.realpath(setup_sandbox_dir) in status_data["stdout"]
    assert "async hello" in status_data["stdout"]
    assert status_data["stderr"] == ""
    assert status_data["exit_code"] == 0


def test_execute_async_command_nonzero_exit(setup_sandbox_dir):
    start_response = client.post(
        "/execute/start",
        json={"command": "python3 -c \"import sys; sys.stderr.write('error output\\n'); sys.exit(7)\""},
    )
    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]

    status_data = None
    for _ in range(50):
        status_response = client.get(f"/execute/status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data["status"] == "completed":
            break
        time.sleep(0.02)

    assert status_data is not None
    assert status_data["status"] == "completed"
    assert "error output" in status_data["stderr"]
    assert status_data["exit_code"] == 7


def test_execute_async_invalid_command(setup_sandbox_dir):
    start_response = client.post(
        "/execute/start",
        json={"command": "nonexistent_binary_xyz_123 --flag"},
    )
    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]

    status_data = None
    for _ in range(25):
        status_response = client.get(f"/execute/status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data["status"] == "completed":
            break
        time.sleep(0.02)

    assert status_data is not None
    assert status_data["status"] == "completed"
    assert status_data["exit_code"] == 1
    assert "Failed to execute command" in status_data["stderr"]


def test_execute_async_command_timeout(setup_sandbox_dir):
    start_response = client.post(
        "/execute/start",
        json={
            "command": "python3 -c \"import time; time.sleep(5)\"",
            "timeout": 0.15,
        },
    )
    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]

    status_data = None
    for _ in range(30):
        status_response = client.get(f"/execute/status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data["status"] == "completed":
            break
        time.sleep(0.02)

    assert status_data is not None
    assert status_data["status"] == "completed"
    assert status_data["exit_code"] == 124
    assert "timed out" in status_data["stderr"].lower()


def test_execute_async_status_unknown_job_id():
    response = client.get("/execute/status/unknown-job-id-999")
    assert response.status_code == 404


def test_execute_async_completed_job_evicted_after_read(setup_sandbox_dir):
    start_response = client.post(
        "/execute/start",
        json={"command": "echo 'cleanup check'"},
    )
    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]

    status_data = None
    for _ in range(30):
        status_response = client.get(f"/execute/status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data["status"] == "completed":
            break
        time.sleep(0.02)

    assert status_data is not None
    assert status_data["status"] == "completed"
    assert "cleanup check" in status_data["stdout"]

    # Subsequent GET /execute/status/{job_id} must return 404 once read
    second_response = client.get(f"/execute/status/{job_id}")
    assert second_response.status_code == 404
    assert second_response.json() == {"message": "Job not found"}

def test_upload_and_download_file(setup_sandbox_dir):
    file_content = b"test file content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    
    assert os.path.exists(os.path.join(setup_sandbox_dir, "test.txt"))
    
    response = client.get("/download/test.txt")
    assert response.status_code == 200
    assert response.content == file_content

def test_list_files(setup_sandbox_dir):
    with open(os.path.join(setup_sandbox_dir, "dummy.txt"), "w") as f:
        f.write("hello")
        
    response = client.get("/list/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(item["name"] == "dummy.txt" for item in data)

def test_exists(setup_sandbox_dir):
    with open(os.path.join(setup_sandbox_dir, "exists.txt"), "w") as f:
        f.write("hello")
        
    response = client.get("/exists/exists.txt")
    assert response.status_code == 200
    assert response.json()["exists"] is True

    response = client.get("/exists/not_exists.txt")
    assert response.status_code == 200
    assert response.json()["exists"] is False
