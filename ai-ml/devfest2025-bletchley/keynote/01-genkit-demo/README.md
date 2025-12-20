# Genkit Demo

This directory contains a simple flow built using [Genkit for Go](https://github.com/firebase/genkit/go).

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

Run the flow using `go run`:

```bash
go run main.go
```

This will execute a predefined flow that asks the model to "Say hello to the world in a creative way!".

### Options

-   **Model Selection:** Use the `-model` flag to specify a different Vertex AI model.
    ```bash
    go run main.go -model vertexai/gemini-2.5-pro
    ```
