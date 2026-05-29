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
import urllib.parse
import asyncio

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

class ExecuteResponse(BaseModel):
    """Response model for the /execute endpoint."""
    stdout: str
    stderr: str
    exit_code: int

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
async def health_check():
    """A simple health check endpoint to confirm the server is running."""
    return {"status": "ok", "message": "Sandbox Runtime is active."}

@app.post("/execute", summary="Execute a shell command", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest):
    """
    Executes a shell command inside the sandbox and returns its output.
    Uses shlex.split for security to prevent shell injection.
    """
    try:
        # Split the command string into a list to safely pass to subprocess
        args = shlex.split(request.command)
        
        # Execute the command from the configured sandbox directory using to_thread to avoid blocking
        process = await asyncio.to_thread(
            subprocess.run,
            args,
            capture_output=True,
            text=True,
            cwd=SANDBOX_DIR 
        )
        return ExecuteResponse(
            stdout=process.stdout,
            stderr=process.stderr,
            exit_code=process.returncode
        )
    except Exception as e:
        logger.exception("Could not execute command, error: '%s'", str(e))
        return ExecuteResponse(
            stdout="",
            stderr=f"Failed to execute command: {str(e)}",
            exit_code=1
        )

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