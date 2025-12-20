# AIDA Project - Gemini Agent Instructions

This document provides specific instructions and context for AI agents (like Gemini) working on the AIDA project.

## Project Overview

AIDA (AI Diagnostic Agent) is a local, privacy-focused diagnostic tool that uses `osquery` and a local RAG system. It's built with Python (FastAPI, google-adk) and uses local LLMs via Ollama.

## Core Mandates for Agents

*   **Follow Existing Conventions**: Match the coding style, naming conventions, and structure of the existing codebase.
*   **Local-First**: Assume the environment is local. Do not introduce dependencies on cloud services unless explicitly requested.
*   **Testing**: All new features and bug fixes must include tests.
*   **Imports**: Use absolute imports for project modules (e.g., `from aida.schema_rag import ...`).

## Development Workflow

### 1. Environment Setup
Ensure you are in the project root. The virtual environment should be active.

### 2. Running Tests
The project uses `unittest` for testing. Run all tests from the project root:
```bash
python3 -m unittest discover tests
```
Always run tests before and after making changes to ensure no regressions.

### 3. Code Style & Linting
Use `ruff` for linting and formatting.
```bash
ruff check . --fix && ruff format .
```

### 4. Project Structure
*   `aida/`: Core package containing agent logic and RAG engines.
    *   `agent.py`: Defines the main agent, tools, and persona.
    *   `schema_rag.py`: RAG engine for osquery schema.
    *   `queries_rag.py`: RAG engine for query packs.
*   `tests/`: Contains `unittest` test files.
    *   `test_aida_core.py`: Core functionality tests.
    *   `test_query_lib.py`: Tests for the query library RAG.
    *   `test_search.py`: Tests for schema search.
*   `main.py`: FastAPI application entry point.
*   `ingest_*.py`: Scripts for data ingestion.

## Key Components

### RAG Engines
The project uses two RAG engines:
*   `schema_rag`: For querying the osquery schema.
*   `queries_rag`: For searching the query library.

Both are initialized in their respective modules in `aida/`. When writing tests, import them directly:
```python
from aida.schema_rag import schema_rag, discover_schema
from aida.queries_rag import queries_rag, search_query_library
```

### Agent Definition
The main agent is defined in `aida/agent.py`. It uses `google.adk` and is configured to use local models (Ollama/Qwen) or Gemini.

## Common Tasks

*   **Adding a new tool**: Define the tool in `aida/agent.py` and register it with the agent. Add corresponding tests in `tests/`.
*   **Modifying RAG logic**: Update `aida/schema_rag.py` or `aida/queries_rag.py`. Ensure you re-run ingestion scripts if the data structure changes.
*   **Updating the UI**: Modify `templates/index.html` or `static/` files.
*   **Updating dependencies**: Add new dependencies to `requirements.txt`.

## Troubleshooting

*   **Import Errors in Tests**: Ensure `sys.path` is correctly set in test files to include the project root.
    ```python
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    ```
*   **RAG Initialization Issues**: The RAG engines require the database files (`schema.db`, `packs.db`) to exist. Run `./setup.sh` if they are missing.