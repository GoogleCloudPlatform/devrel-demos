# Go for GenAI! - Project Context

This repository contains the companion code for the "Go for GenAI!" keynote at DevFest Bletchley Park 2025. It demonstrates how to build Generative AI applications in Go using two primary frameworks: the **Agent Development Kit (ADK)** and **Genkit**.

## Project Structure

The project is organized into two main demonstration directories, sharing a common root `go.mod`.

*   **`01-genkit-demo/`**: A structured workflow built with [Genkit for Go](https://github.com/firebase/genkit/go). It showcases linear, prompt-driven flows.
*   **`02-genkit-server-demo/`**: A simple flow server built with Genkit. It demonstrates how to run a flow as a server for UI interaction.
*   **`03-adk-demo/`**: A conversational agent built with the [Agent Development Kit (ADK) for Go](https://github.com/googleapis/adk-go). It showcases stateful, interactive agents.

## Key Technologies

*   **Language:** Go 1.24+
*   **AI Backend:** Google Vertex AI (Gemini Models)
*   **Frameworks:**
    *   `google.golang.org/adk`
    *   `github.com/firebase/genkit/go`

## Building and Running

### Prerequisites

1.  **Go:** Version 1.24 or later.
2.  **Google Cloud:**
    *   A Google Cloud Project with the **Vertex AI API** enabled.
    *   **Google Cloud CLI (`gcloud`)** installed and authenticated.
    *   Run `gcloud auth application-default login` to set up Application Default Credentials.
3.  **Genkit CLI:** (Optional, for UI interaction)
    *   Install via script: `curl -sL cli.genkit.dev | bash`

### Environment Setup

Set the required environment variables before running either demo:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1" # Optional, defaults to us-central1
```

### Running the Genkit Demo

The Genkit demo executes a simple flow to generate a creative greeting.

*   **Default Run:**
    ```bash
    go run 01-genkit-demo/main.go
    ```
*   **Specify Model:**
    ```bash
    go run 01-genkit-demo/main.go -model vertexai/gemini-2.5-pro
    ```
    *Note: Defaults to `vertexai/gemini-2.5-flash`.*

### Running the Genkit Server Demo

The Genkit Server demo runs a flow server.

*   **Default Run:**
    ```bash
    go run 02-genkit-server-demo/main.go
    ```
*   **Specify Model:**
    ```bash
    go run 02-genkit-server-demo/main.go -model vertexai/gemini-2.5-pro
    ```

### Running the ADK Demo

The ADK demo runs a "Hello World" agent.

*   **Default Run (Console Mode):**
    ```bash
    go run 03-adk-demo/main.go
    ```
*   **Specify Model:**
    ```bash
    go run 03-adk-demo/main.go -model gemini-2.5-pro
    ```
    *Note: Defaults to `gemini-2.5-flash`.*
*   **Web Mode (starts API and Web UI):**
    ```bash
    go run 03-adk-demo/main.go web api webui
    ```

## Development Conventions

*   **Model Selection:**
    *   **Default:** `gemini-2.5-flash` (or `vertexai/gemini-2.5-flash` for Genkit).
    *   **High Capability:** Use `gemini-2.5-pro` when advanced reasoning is required.
    *   **Deprecated:** Do not use Gemini 1.5 models.
*   **Dependency Management:** All dependencies are managed in the root `go.mod`. Run `go mod tidy` from the root directory if you add new imports.
*   **Authentication:** The project relies on Google Cloud Application Default Credentials (ADC). Do not hardcode API keys.
