# Multi-LLM UI

This is a Next.js application that provides a user interface for interacting with multiple Large Language Models (LLMs) simultaneously.

## Features

*   **Side-by-side comparison:**  Send the same prompt to multiple LLMs and compare their responses in a single view.
*   **Adjustable parameters:** Control the temperature and maximum number of tokens for each generation.
*   **Dynamic model loading:** The list of available LLMs is dynamically loaded from an environment variable.
*   **Containerized:** The application can be easily deployed using Docker and Kubernetes.

## Getting Started

### Prerequisites

*   Node.js (v18 or later)
*   npm, yarn, pnpm, or bun

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
    cd devrel-demos/containers/multi-llm-ui
    ```

2.  Install the dependencies:

    ```bash
    npm install
    ```

### LLMs

This application assumes you have LLMs running and accessible via HTTP. You can look at `k8s/` folder for instruction on how to deploy an LLM with the OpenAI compatible api.

This repo has examples with vLLM, TGI and ollama and uses GPU and TPU.

### Configuration

1.  Create a `.env.local` file in the root of the project.
2.  Add the following environment variable to the `.env.local` file:

    ```
    LLM_URLS=http://localhost:8080,http://localhost:8081
    ```

    Replace the URLs with the actual URLs of your LLM APIs. The application expects the LLM APIs to be compatible with the OpenAI API standard, with the following endpoints:
    *   `/v1/models`
    *   `/v1/chat/completions`

### Running the development server

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

## Deployment

### Docker

The repository includes a `Dockerfile` that can be used to build a Docker image of the application.

```bash
docker build -t multi-llm-ui .
docker run -p 3000:3000 -e LLM_URLS="http://<your-llm-api-1>,http://<your-llm-api-2>" multi-llm-ui
```

### Kubernetes

The `k8s` directory contains Kubernetes manifests for deploying the application and various LLMs.

## License

Licensed under the [MIT license](https://github.com/heroui-inc/next-app-template/blob/main/LICENSE).