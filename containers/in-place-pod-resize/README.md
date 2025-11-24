# IPPR

IPPR is a Go-based web service designed to interact with the Kubernetes API. It provides endpoints to view and dynamically update the CPU and memory resources of a Kubernetes pod. The application can run both inside and outside a Kubernetes cluster, automatically detecting its environment to configure the Kubernetes client.

## Building and Running

### Prerequisites

*   Go (version 1.22 or later)
*   Docker
*   A Kubernetes cluster (e.g., Minikube, Kind, or a cloud-based provider)
*   `kubectl` configured to interact with your cluster

### Local Development

To run the application locally, you will need to have a Kubernetes cluster accessible and your `kubeconfig` file properly configured.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
    cd containers/in-place-pod-resize
    ```

2.  **Run the application:**
    ```bash
    go run .
    ```
    The application will start on port 8080. By default, it will try to connect to a pod named `ippr` in the `ippr` namespace. You can change this by setting the `POD_NAME` and `NAMESPACE` environment variables.

### Docker Build

To build the Docker image:

```bash
docker build -t ippr:latest .
```

The `Dockerfile` uses a multi-stage build to create a minimal final image.

### Kubernetes Deployment

The `k8s` directory contains the necessary Kubernetes manifests to deploy the application.

1.  **Apply the manifests:**
    ```bash
    ./k8s/deploy.sh
    ```

This will create a pod, a service account, and a service in the `ippr` namespace.
