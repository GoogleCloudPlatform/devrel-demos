# ADK Demo

This directory contains a "Hello World" agent built using the [Agent Development Kit (ADK) for Go](https://github.com/googleapis/adk-go).

## Prerequisites

-   Go 1.24 or later.
-   A Google Cloud Project with Vertex AI API enabled.
-   [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated (`gcloud auth application-default login`).

## Configuration

Set the following environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1" # Optional, defaults to us-central1
```

## Running the Demo

You can run the agent directly using `go run`:

```bash
go run main.go
```

By default, this starts an interactive console session with the agent.

### Options

-   **Model Selection:** Use the `-model` flag to specify a different Gemini model.
    ```bash
    go run main.go -model gemini-2.5-pro
    ```

-   **Launcher Modes:** The ADK launcher supports different modes (passed as arguments after flags).
    -   `console` (default): Interactive CLI chat.
    -   `web`: Starts a web server for the agent. Requires specifying sublaunchers (e.g., `api`, `webui`).

    Example running in web mode (starts API and Web UI):
    ```bash
    go run main.go web api webui
    ```
