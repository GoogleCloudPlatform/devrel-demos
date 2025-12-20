# Genkit Server Demo

This directory contains a simple flow built using [Genkit for Go](https://github.com/firebase/genkit/go). It runs as a server, allowing interaction via the Genkit Developer UI.

## Prerequisites

-   Go 1.24 or later.
-   A Google Cloud Project with Vertex AI API enabled.
-   [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated (`gcloud auth application-default login`).
-   [Genkit CLI](https://firebase.google.com/docs/genkit/get-started) (optional, for UI interaction).

## Configuration

Set the following environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1" # Optional, defaults to us-central1
```

## Running the Demo

Start the flow server:

```bash
go run main.go
```

### Interaction

This application runs as a Genkit server. You can interact with it using the Genkit Developer UI:

```bash
genkit start -- go run main.go
```

Or by sending requests to the exposed flow endpoint if running standalone.

### Options

-   **Model Selection:** Use the `-model` flag to specify a different Vertex AI model.
    ```bash
    go run main.go -model vertexai/gemini-2.5-pro
    ```
