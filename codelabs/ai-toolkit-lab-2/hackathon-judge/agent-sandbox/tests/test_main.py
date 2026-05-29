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

def test_execute_command(setup_sandbox_dir):
    response = client.post("/execute", json={"command": "echo 'hello world'"})
    assert response.status_code == 200
    data = response.json()
    assert "hello world" in data["stdout"]
    assert data["exit_code"] == 0

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
