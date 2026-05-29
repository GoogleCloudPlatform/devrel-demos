# Agent Sandbox

The Agent Sandbox is a secure execution runtime built with **Python** and **FastAPI**. It provides a restricted environment where the primary AI agent can safely execute commands and interact with files from untrusted hackathon project submissions.

## Features

- **Command Execution (`/execute`)**: Safely executes shell commands within a confined directory (`/app` by default) using `subprocess` and `shlex` to prevent shell injection.
- **File Management**: Provides endpoints to upload (`/upload`), download (`/download`), list (`/list`), and check for the existence (`/exists`) of files and directories within the sandbox.
- **Path Sanitization**: Ensures all file operations remain strictly within the designated sandbox directory, preventing unauthorized access to the host file system.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

## Installation

Install dependencies using `uv`:

```bash
uv sync
```

## Running the Application

You can start the FastAPI server using `uv`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

By default, the sandbox operates in the `/app` directory (or the path defined by the `SANDBOX_DIR` environment variable).

## API Endpoints

- `GET /`: Health check.
- `POST /execute`: Execute a shell command.
- `POST /upload`: Upload a file to the sandbox.
- `GET /download/{encoded_file_path}`: Download a file from the sandbox.
- `GET /list/{encoded_file_path}`: List contents of a directory.
- `GET /exists/{encoded_file_path}`: Check if a path exists.