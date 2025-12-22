# Gemini Diagnostic Agent

This repository is the companion project for the talk "How to create a diagnostic agent with Gemini and osquery". It showcases the development of a diagnostic agent through several versions, each adding more capabilities.

The project includes a FastAPI web application that serves a simple chat interface to interact with the agent. The backend is powered by the agent from the `v4` directory.

## Features

*   **Diagnostic Agent:** An AI agent powered by Gemini that can perform system diagnostics using osquery.
*   **Web Interface:** A simple chat interface to interact with the agent.
*   **Evolving Agent:** The repository contains multiple versions of the agent, showing the evolution of its capabilities.
*   **Tool-based:** The agent uses a variety of tools to perform its tasks, including running osquery commands, searching the web, and discovering osquery schemas.

## Getting Started

### Prerequisites

*   Python 3.7+
*   pip
*   [osquery](https://osquery.io/downloads/official/)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/biznaga.git
    cd biznaga
    ```
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  Create a `.env` file in the root of the project:
    ```bash
    touch .env
    ```
2.  Add the following environment variables to the `.env` file:
    ```
    PROJECT_ID="your-gcp-project-id"
    LOCATION="your-gcp-location"
    RAG_CORPORA_URI="your-rag-corpora-uri"
    ```

## Usage

1.  Run the FastAPI application:
    ```bash
    uvicorn main:app --reload
    ```
2.  Open your browser and navigate to `http://127.0.0.1:8000` to interact with the agent.

## Agent Versions

This repository contains several versions of the diagnostic agent, each in its own directory. Here's a brief overview of the evolution of the agent:

### v1: The Basic Agent

The first version of the agent is a simple agent that can run osquery commands. It has a single tool, `run_osquery`, which allows it to execute osquery queries and get the results.

### v2: The Context-Aware Agent

The second version of the agent is more context-aware. It knows the operating system it's running on and the available osquery tables. This allows it to provide more accurate and relevant information.

### v3: The Web-Enabled Agent

The third version of the agent adds a `google_search` tool, which allows it to search the web for information. This is useful for finding information about osquery tables, queries, and other system-related topics.

### v4: The Schema-Aware Agent

The fourth version of the agent is the most advanced. It adds a `discover_schema` tool, which allows it to discover osquery table schemas based on a search phrase. This makes the agent more powerful and flexible, as it can now discover the information it needs to construct its queries.

### v4-live: The Live API Agent

This version showcases the Gemini Live API and a live model (`gemini-live-2.5-flash-preview-native-audio`). It is not a production-ready agent, but rather a demonstration of how to integrate real-time models into the agent framework. It also includes enhanced logging for better introspection into tool usage.

### v5: The Multi-Agent System

The fifth version refactors the single-agent architecture into a more sophisticated multi-agent system. It introduces a sequential pipeline that breaks the diagnostic process into three distinct stages, each handled by a specialized agent:
*   **Query Planner:**  Determines the necessary osquery queries to investigate an issue.
*   **Query Executor:** Runs the queries and handles potential errors.
*   **Data Analyser:**  Summarizes the results from the executed queries to provide a concise analysis.
This version represents a shift towards a more modular and powerful agent design.

## API Endpoints

The FastAPI application provides the following endpoints:

*   `GET /`: Serves the HTML chat interface.
*   `POST /chat`: Handles the chat logic and streams the agent's response.
*   `GET /idle`: Returns the idle image for the agent's avatar.
*   `GET /talk`: Returns the talking image for the agent's avatar.
*   `GET /random_image`: Returns a random image from the `assets` folder.