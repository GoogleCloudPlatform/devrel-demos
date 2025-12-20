# AIDA - AI Diagnostic Agent

AIDA is a local, privacy-focused emergency diagnostic agent. It leverages `osquery` to inspect system state and uses a sophisticated local RAG (Retrieval-Augmented Generation) system to understand osquery's extensive schema and utilize expert-written query packs.

**Official Website:** [DevFest Scotland 2025](https://devfestscotland.com/)

**Slides:** [How to Build a Diagnostic Agent](https://speakerdeck.com/danicat/how-to-create-a-diagnostic-agent-with-gemini-and-osquery)

![AIDA Interface](aida_v3.png)

## Key Features

*   **100% Local & Private**: Runs entirely on your machine using local LLMs (via Ollama) and on-device embedding models.
*   **Multi-Model Support**: Switch seamlessly between **Gemini 2.5 Flash**, **Qwen 2.5**, and **GPT-OSS** directly from the UI.
*   **Osquery Expert**: Grounded in the official osquery schema and standard query packs.
*   **Persistent RAG Engine**: High-performance, low-latency RAG using a persistent in-memory embedding model (Gemma-300M).
*   **Query Library**: Instantly recalls hundreds of expert queries for complex tasks like malware hunting, filtered by your operating system.
*   **Schema Discovery**: Can find and understand any of the 280+ osquery tables to construct custom queries on the fly.
*   **Enhanced UI**: Retro-styled interface with real-time memory usage tracking, debug mode for tool inspection, markdown rendering, and session management.

## Architecture

*   **Agent Framework**: Built with `google.adk`.
*   **LLM**: Supports **Gemini 2.5 Flash**, **Qwen 2.5**, and **GPT-OSS** (via Ollama) for reasoning and tool use.
*   **RAG System**: Pure SQLite implementation using `sqlite-vec` (vector search) and `sqlite-ai` (in-database embeddings).
*   **Interface**: FastAPI backend serving a retro-styled HTML/JS frontend.

## Prerequisites

*   Python 3.12+
*   `git`
*   **Ollama** running locally (`ollama serve`) for local models.
*   `osquery` installed on the host system.

## Configuration

The project requires the following environment variables to be set, either in your shell or in a `.env` file within the `aida_v*` directories:

*   `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID.
*   `GOOGLE_CLOUD_LOCATION`: The location for Vertex AI (e.g., `us-central1` or `global`).
*   `GOOGLE_GENAI_USE_VERTEXAI`: Set to `1` to enable Vertex AI.

## Quick Start

1.  **Setup**: Run the automated setup script to install dependencies, fetch osquery data, download models, and build the knowledge base.
    ```bash
    ./setup.sh
    ```
    *(This may take a few minutes as it downloads a ~300MB embedding model and ingests data.)*

2.  **Run**: Start the agent server.
    ```bash
    uvicorn main:app --reload
    ```

3.  **Interact**: Open `http://127.0.0.1:8000` in your browser.

## Development

*   **Tests**: Run the test suite using `unittest`.
    ```bash
    python3 -m unittest discover tests
    ```
*   **Linting**: Keep the code clean.
    ```bash
    ruff check . --fix && ruff format .
    ```

## Project Structure

*   `aida/agent.py`: Core agent definition, persona, and tools.
*   `aida/schema_rag.py`: RAG engine for schema discovery.
*   `aida/queries_rag.py`: RAG engine for pre-defined query packs.
*   `ingest_osquery.py`: Ingests `.table` schema definitions into `osquery.db`.
*   `ingest_packs.py`: Ingests standard `.conf` query packs into `osquery.db`.
*   `main.py`: FastAPI application and web UI.
*   `tests/`: Unit and integration tests.
*   `static/`: Frontend assets (CSS, JS, libraries).
*   `templates/`: HTML templates.
