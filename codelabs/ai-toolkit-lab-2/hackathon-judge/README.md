# Hackathon Judge

This repository contains the code for a **Hackathon Judging Agent**, a comprehensive system designed to automate and assist in the evaluation of hackathon projects. 

## Overall Purpose

The Hackathon Judge platform automates project review, scoring, and feedback generation using AI agents. By integrating a multi-component architecture, it reliably evaluates code submissions and provides structured feedback to participants.

## Core Components

The repository is structured into several interconnected projects:

- **[`frontend`](./frontend/README.md)**: A React + TypeScript application (built with Vite) that provides the user interface for administrators and judges.
- **[`backend`](./backend/README.md)**: A robust Go-based REST API that manages hackathon data, projects, and evaluations, utilizing Google Cloud BigQuery for storage and Google Cloud Pub/Sub for asynchronous task queuing.
- **[`agent`](./agent/README.md)**: A Python application powered by the Google ADK (Agent Development Kit). It listens for judging tasks via Pub/Sub, processes the projects using large language models, and publishes the evaluation results.
- **[`agent-sandbox`](./agent-sandbox/README.md)**: A secure execution environment built with FastAPI. It provides an API for the agent to safely execute shell commands and manipulate files during the evaluation of a project's codebase.

## Key Features & Infrastructure

- **Agent Sandbox**: The system leverages a dedicated, secure sandbox environment (`agent-sandbox`) to evaluate untrusted code submissions safely without compromising the main agent's integrity.
- **Google Kubernetes Engine (GKE)**: Designed to be deployed on GKE, providing scalable, containerized execution for both the backend services and the worker agents.
- **Event-Driven Architecture**: Uses Google Cloud Pub/Sub to decouple the API from the heavy lifting of the AI agents, ensuring the system remains responsive even under high load.
- **Google Cloud BigQuery**: Serves as the primary data warehouse for storing hackathon metadata and evaluation results.
