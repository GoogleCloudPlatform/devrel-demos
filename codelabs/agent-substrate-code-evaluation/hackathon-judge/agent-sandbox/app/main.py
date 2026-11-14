# Copyright 2025 The Kubernetes Authors.
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

import subprocess
import os
import shlex
import logging
import time
import urllib.parse
import asyncio
from dataclasses import dataclass
import threading
import uuid

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys

SANDBOX_DIR = os.getenv("SANDBOX_DIR")
if not SANDBOX_DIR:
    print("Error: SANDBOX_DIR environment variable is required", file=sys.stderr)
    sys.exit(1)

class ExecuteRequest(BaseModel):
    """Request model for the /execute endpoint."""
    command: str


class ExecuteStartRequest(BaseModel):
    """Request model for the /execute/start endpoint."""
    command: str
    timeout: float | None = 600.0

class ExecuteResponse(BaseModel):
    """Response model for the /execute endpoint."""
    stdout: str
    stderr: str
    exit_code: int


class ExecuteStartResponse(BaseModel):
    """Response model for the /execute/start endpoint."""
    job_id: str
    status: str


class ExecuteStatusResponse(BaseModel):
    """Response model for the /execute/status/{job_id} endpoint."""
    job_id: str
    status: str
    stdout: str
    stderr: str
    exit_code: int | None


@dataclass
class _JobState:
    """In-memory state for an asynchronous command execution job."""
    job_id: str
    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    completed_at: float | None = None


_JOB_TTL_SECONDS = 300.0
_jobs: dict[str, _JobState] = {}
_jobs_lock = threading.Lock()


def _sweep_expired_jobs_locked(now: float) -> None:
    """Removes completed jobs older than _JOB_TTL_SECONDS. Caller must hold _jobs_lock."""
    expired_ids = [
        jid
        for jid, state in _jobs.items()
        if state.completed_at is not None
        and (now - state.completed_at) > _JOB_TTL_SECONDS
    ]
    for jid in expired_ids:
        _jobs.pop(jid, None)


def _run_subprocess(
    command: str,
    timeout: float | None = None,
    cwd: str | None = None,
) -> ExecuteResponse:
    """Runs a shell command safely via shlex.split and subprocess.run."""
    work_dir = cwd if cwd is not None else SANDBOX_DIR
    try:
        args = shlex.split(command)
        process = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=work_dir,
            timeout=timeout,
        )
        return ExecuteResponse(
            stdout=process.stdout,
            stderr=process.stderr,
            exit_code=process.returncode,
        )
    except subprocess.TimeoutExpired as e:
        stdout = (
            e.stdout.decode("utf-8", errors="replace")
            if isinstance(e.stdout, bytes)
            else (e.stdout or "")
        )
        stderr = (
            e.stderr.decode("utf-8", errors="replace")
            if isinstance(e.stderr, bytes)
            else (e.stderr or "")
        )
        timeout_msg = f"Command timed out after {timeout} seconds"
        stderr = f"{stderr}\n{timeout_msg}".strip() if stderr else timeout_msg
        return ExecuteResponse(
            stdout=stdout,
            stderr=stderr,
            exit_code=124,
        )
    except Exception as e:
        logger.exception("Could not execute command, error: '%s'", str(e))
        return ExecuteResponse(
            stdout="",
            stderr=f"Failed to execute command: {str(e)}",
            exit_code=1,
        )


def get_safe_path(file_path: str) -> str:
    """Sanitizes the file path to ensure it stays within the sandbox directory."""
    base_dir = os.path.realpath(SANDBOX_DIR)
    # Remove leading slashes to ensure path is relative
    clean_path = file_path.lstrip("/")
    full_path = os.path.realpath(os.path.join(base_dir, clean_path))

    if os.path.commonpath([base_dir, full_path]) != base_dir:
        raise ValueError(f"Access denied: Path must be within {SANDBOX_DIR}")
    
    return full_path

app = FastAPI(
    title="Agentic Sandbox Runtime",
    description="An API server for executing commands and managing files in a secure sandbox.",
    version="1.0.0",
)

@app.get("/", summary="Health Check")
@app.get("/health", summary="Health Check")
async def health_check():
    """A simple health check endpoint to confirm the server is running."""
    return {"status": "ok", "message": "Sandbox Runtime is active."}

@app.post("/execute", summary="Execute a shell command", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest) -> ExecuteResponse:
    """
    Executes a shell command inside the sandbox and returns its output.
    Uses shlex.split for security to prevent shell injection.
    """
    return await asyncio.to_thread(_run_subprocess, request.command)


def _run_async_command(
    job_id: str,
    command: str,
    cwd: str,
    timeout: float | None = 600.0,
) -> None:
    result = _run_subprocess(command, timeout=timeout, cwd=cwd)
    with _jobs_lock:
        _jobs[job_id] = _JobState(
            job_id=job_id,
            status="completed",
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            completed_at=time.monotonic(),
        )


@app.post("/execute/start", summary="Start a shell command asynchronously", response_model=ExecuteStartResponse)
async def execute_command_start(request: ExecuteStartRequest) -> ExecuteStartResponse:
    """Spawns a shell command asynchronously inside the sandbox and returns its job_id."""
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _sweep_expired_jobs_locked(time.monotonic())
        _jobs[job_id] = _JobState(
            job_id=job_id,
            status="running",
        )
    thread = threading.Thread(
        target=_run_async_command,
        args=(job_id, request.command, SANDBOX_DIR, request.timeout),
        daemon=True,
    )
    thread.start()
    return ExecuteStartResponse(job_id=job_id, status="running")


@app.get("/execute/status/{job_id}", summary="Poll status of an asynchronous command", response_model=ExecuteStatusResponse)
async def execute_command_status(job_id: str) -> ExecuteStatusResponse | JSONResponse:
    """Returns the current status and output of an asynchronous command execution."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is not None:
            if job.status in ("completed", "failed"):
                _jobs.pop(job_id, None)
            return ExecuteStatusResponse(
                job_id=job.job_id,
                status=job.status,
                stdout=job.stdout,
                stderr=job.stderr,
                exit_code=job.exit_code,
            )
    return JSONResponse(status_code=404, content={"message": "Job not found"})

@app.post("/upload", summary="Upload a file to the sandbox")
async def upload_file(path: str | None = None, file: UploadFile = File(...)):
    """
    Receives a file and saves it to the /app directory in the sandbox.
    """
    try:
        logging.info(f"--- UPLOAD_FILE CALLED: Attempting to save '{file.filename}' (requested path: '{path}') ---")
        if path is not None:
            file_path = get_safe_path(path)
        else:
            file_path = get_safe_path(file.filename)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        filename_to_return = path if path else file.filename
        return JSONResponse(
            status_code=200,
            content={"message": f"File '{filename_to_return}' uploaded successfully."}
        )
    except ValueError as e:
        return JSONResponse(
            status_code=403,
            content={"message": f"Access denied: {str(e)}"}
        )
    except Exception as e:
        logging.exception("An error occurred during file upload.")
        return JSONResponse(
            status_code=500,
            content={"message": f"File upload failed: {str(e)}"}
        )


@app.get("/download/{encoded_file_path:path}", summary="Download a file from the sandbox")
async def download_file(encoded_file_path: str):
    """
    Downloads a specified file from the sandbox directory.
    """
    decoded_path = urllib.parse.unquote(encoded_file_path)
    try:
        full_path = get_safe_path(decoded_path)
    except ValueError as e:
        logger.warning("Access denied downloading file '%s': %s", decoded_path, e)
        return JSONResponse(status_code=403, content={"message": "Access denied"})
    except Exception as e:
        logger.exception("Unexpected error resolving path for download '%s'", decoded_path)
        return JSONResponse(status_code=500, content={"message": "Internal server error"})

    if os.path.isfile(full_path):
        return FileResponse(path=full_path, media_type='application/octet-stream', filename=decoded_path)

    logger.error("File not found for download: '%s'", full_path)
    return JSONResponse(status_code=404, content={"message": "File not found"})


@app.get("/list/{encoded_file_path:path}", summary="List files in a directory")
async def list_files(encoded_file_path: str):
    """
    Lists the contents of a directory under the sandbox directory.
    """
    decoded_path = urllib.parse.unquote(encoded_file_path)
    try:
        full_path = get_safe_path(decoded_path)
    except ValueError:
        return JSONResponse(status_code=403, content={"message": "Access denied"})

    def get_entries():
        if not os.path.isdir(full_path):
            return None
        entries = []
        with os.scandir(full_path) as it:
            for entry in it:
                stats = entry.stat()
                entries.append({
                    "name": entry.name,
                    "size": stats.st_size,
                    "type": "directory" if entry.is_dir() else "file",
                    "mod_time": stats.st_mtime
                })
        return entries

    try:
        entries = await asyncio.to_thread(get_entries)
        if entries is None:
            return JSONResponse(status_code=404, content={"message": "Path is not a directory"})
        return JSONResponse(status_code=200, content=entries)
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"List files failed: {str(e)}"})


@app.get("/exists/{encoded_file_path:path}", summary="Check if the relative path exists")
async def exists(encoded_file_path: str):
    """
    Checks if a specified file or directory exists under the sandbox directory.
    """
    decoded_path = urllib.parse.unquote(encoded_file_path)
    try:
        full_path = get_safe_path(decoded_path)
    except ValueError:
        return JSONResponse(status_code=403, content={"message": "Access denied"})

    return JSONResponse(status_code=200, content={
        "path": decoded_path,
        "exists": os.path.exists(full_path)
    })