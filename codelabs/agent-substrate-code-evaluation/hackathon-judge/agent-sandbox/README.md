# Judge Actor Runtime (`agent-sandbox`)

The Judge Actor runtime (`agent-sandbox`) is a secure execution environment built with **Python**, **FastAPI**, and the **Google Antigravity SDK**. Packaged into an **Agent Substrate** (`v1.0.0`) **ActorTemplate** (`judge-sandbox`) and checkpointed as a memory-fidelity **Golden Snapshot**, each ephemeral **Judge Actor** runs inside a gVisor sandbox with zero Google Cloud credentials to safely clone, build, test, and evaluate untrusted hackathon project submissions.

## Features

- **Asynchronous Command Execution (`POST /execute/start` & `GET /execute/status/{job_id}`)**: Starts long-running commands (`git clone`, `uv run python -m app.judge`) in a background task and returns a `job_id` immediately so requests traversing `atenet-router` never hit Envoy stream idle timeouts.
- **Synchronous Command Execution (`POST /execute`)**: Executes short shell commands within the configured `SANDBOX_DIR` (`/home/sandbox/app` in the container) using `shlex` argument splitting.
- **Zero-Credential Autonomous Judge (`app/judge.py`)**: Runs the Antigravity SDK local agent loop (`python -m app.judge`). When `MODEL_PROXY_BASE_URL` is configured, it routes all Gemini requests through the Judge Orchestrator's **Model Proxy** (`http://agent.hackathon-judge.svc.cluster.local:8000/vertex-proxy`) without accessing GCP Application Default Credentials or the GKE metadata server.
- **File Management & Path Sanitization**: Provides endpoints to upload (`/upload`), download (`/download/{encoded_file_path}`), list (`/list/{encoded_file_path}`), and check existence (`/exists/{encoded_file_path}`) strictly within the sandbox directory.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

## Installation

Install dependencies using `uv`:

```bash
uv sync
```

## Running the Application

Start the FastAPI server using `uv`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8888
```

## API Endpoints

- `GET /` and `GET /health`: Health and wakeup probes (`200 OK`).
- `POST /execute/start`: Start an asynchronous shell command and return `{"job_id": "<id>", "status": "running"}`.
- `GET /execute/status/{job_id}`: Poll the status, `stdout`, `stderr`, and `exit_code` of an asynchronous command job.
- `POST /execute`: Execute a synchronous shell command.
- `POST /upload`: Upload a file to the sandbox workspace.
- `GET /download/{encoded_file_path}`: Download a file from the sandbox workspace.
- `GET /list/{encoded_file_path}`: List contents of a directory.
- `GET /exists/{encoded_file_path}`: Check if a path exists.
