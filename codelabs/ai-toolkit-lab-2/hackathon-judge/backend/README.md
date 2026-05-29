# Backend API

The backend is a high-performance REST API built in **Go** using the Gin web framework. It serves as the central data manager and task orchestrator for the Hackathon Judge system.

## Features

- **Data Management**: Handles CRUD operations for hackathons, projects, and evaluations.
- **BigQuery Integration**: Uses Google Cloud BigQuery as the primary persistent data store for scalability and analytics.
- **Asynchronous Task Queuing**: Integrates with Google Cloud Pub/Sub to publish evaluation tasks to the AI agents and subscribe to completed results.
- **Clean Architecture**: Structured using domain-driven design principles for clear separation of concerns (handlers, services, repositories).

## Prerequisites

- Go 1.21+
- Google Cloud Project with BigQuery and Pub/Sub enabled
- A valid `.env` file or exported environment variables

## Environment Variables

The backend relies on several environment variables, which can be provided via a `.env` file:

- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID (defaults to `mofilabs`).
- `TASKS_TOPIC`: Pub/Sub topic for publishing judging tasks (defaults to `judging-tasks`).
- `RESULTS_SUB`: Pub/Sub subscription for receiving evaluation results (defaults to `backend-judging-results-sub`).

## Running the Application

To run the backend server locally:

```bash
cd cmd/api
go run main.go
```

The server will start on port `8080` by default.