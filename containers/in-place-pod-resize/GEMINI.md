# Project Overview

This project, `ippr`, is a Go-based web service designed to interact with the Kubernetes API. It provides endpoints to view and dynamically update the CPU and memory resources of a Kubernetes pod. The application can run both inside and outside a Kubernetes cluster, automatically detecting its environment to configure the Kubernetes client.

## Key Technologies

*   **Go:** The primary programming language.
*   **Kubernetes:** The application interacts with the Kubernetes API to manage pod resources.
*   **Docker:** The application is containerized for deployment in a Kubernetes environment.

## Architecture

The application consists of a single Go binary that runs a web server. The server exposes a simple API to query and patch the resources of a specific pod. The pod to be targeted is determined by the `POD_NAME` and `NAMESPACE` environment variables.

The application serves a simple HTML interface from an embedded `templates` directory.

# Building and Running

## Prerequisites

*   Go (version 1.22 or later)
*   Docker
*   A Kubernetes cluster (e.g., Minikube, Kind, or a cloud-based provider)
*   `kubectl` configured to interact with your cluster

## Local Development

To run the application locally, you will need to have a Kubernetes cluster accessible and your `kubeconfig` file properly configured.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/moficodes/ippr.git
    cd ippr
    ```

2.  **Run the application:**
    ```bash
    go run .
    ```
    The application will start on port 8080. By default, it will try to connect to a pod named `ippr` in the `ippr` namespace. You can change this by setting the `POD_NAME` and `NAMESPACE` environment variables.

## Docker Build

To build the Docker image:

```bash
docker build -t ippr:latest .
```

The `Dockerfile` uses a multi-stage build to create a minimal final image.

## Kubernetes Deployment

The `k8s` directory contains the necessary Kubernetes manifests to deploy the application.

1.  **Create the namespace:**
    ```bash
    kubectl create namespace ippr
    ```

2.  **Apply the manifests:**
    ```bash
    kubectl apply -f k8s/
    ```

This will create a pod, a service account, and a service in the `ippr` namespace.

# Development Conventions

The codebase is structured into two main files:

*   `main.go`: Handles the initialization of the Kubernetes client, sets up the HTTP server, and defines the routes.
*   `handler.go`: Contains the HTTP handler functions that implement the API logic for interacting with the Kubernetes API.

The application uses the official Go client for Kubernetes (`k8s.io/client-go`) to interact with the cluster.

The frontend is a simple HTML page with JavaScript that makes AJAX calls to the backend API.

# Workflow

- Anytime you are working on a features create a plan that details a step by step process.
- You may create plans in `plans/` folder (create if it doesnt exist). Name the plan after the feature requested.
