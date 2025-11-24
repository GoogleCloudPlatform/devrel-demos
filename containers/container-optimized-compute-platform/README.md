# Are You Faster Than Container Optimized Compute?

This project is a web-based game that tests your reaction time against the scaling speed of a Kubernetes deployment.

## Running Locally

Follow these instructions to run the application on your local machine for development or testing.

### Prerequisites

Ensure you have the following tools installed and configured on your system:

- **Go**: [Installation Guide](https://golang.org/doc/install)
- **Node.js & npm**: [Installation Guide](https://nodejs.org/en/download/)
- **kubectl**: [Installation Guide](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- A running Kubernetes cluster and a configured `kubeconfig` file (`~/.kube/config`).

### 1. Build the Frontend

The frontend is a Next.js application located in the `client` directory. You need to install its dependencies and build the static files that will be served by the Go backend.

```bash
# Navigate to the client directory
cd client

# Install dependencies
npm install

# Build the static assets
npm run build
```

This will create a `client/out` directory containing the static frontend assets.

### 2. Run the Backend

The backend is a Go server that handles game logic, WebSocket communication, and serves the frontend. Run it from the root of the project.

```bash
# Navigate back to the project root (if you were in the client directory)
cd ..

# Run the Go server
go run main.go
```

The server will start on port `8080` by default.

### 3. Play the Game

Once the backend is running, open your web browser and navigate to:

[http://localhost:8080](http://localhost:8080)

You should see the game interface. Enjoy!
