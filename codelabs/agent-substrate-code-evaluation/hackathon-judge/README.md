# Hackathon Judge

This repository contains the code for a **Hackathon Judging Agent**, a comprehensive system designed to automate and assist in the evaluation of hackathon projects on Google Kubernetes Engine (GKE) with **Agent Substrate** (`v1.0.0`).

## Overall Purpose

The Hackathon Judge platform automates project review, scoring, and feedback generation using AI agents. By combining an event-driven microservice architecture with ephemeral, zero-credential **Judge Actors** restored from a memory-fidelity **Golden Snapshot** on **Agent Substrate**, it safely clones, builds, tests, and scores untrusted code submissions and provides structured feedback to participants.

## Core Components

The repository is structured into four interconnected services:

- **[`frontend`](./frontend/README.md)**: A React + TypeScript application (built with Vite) that provides the user interface for administrators and judges.
- **[`backend`](./backend/README.md)**: A Go REST API that manages hackathon data, projects, and evaluations, utilizing Google Cloud BigQuery for storage and Google Cloud Pub/Sub for asynchronous task queuing.
- **[`agent`](./agent/README.md)**: The **Judge Orchestrator** — a Python application powered by the Google ADK (Agent Development Kit). It listens for **Judging Tasks** via Pub/Sub, provisions ephemeral **Judge Actors** via `kubectl-ate` and `atenet-router`, hosts the internal **Model Proxy** (`/vertex-proxy`) backed by **Gemini on Agent Platform**, and publishes **Evaluation Results**.
- **[`agent-sandbox`](./agent-sandbox/README.md)**: The **Judge Actor** runtime image built with FastAPI and the Google Antigravity SDK. Each Judge Actor runs inside an isolated gVisor sandbox on an Agent Substrate **WorkerPool**, exposes asynchronous command execution (`/execute/start`, `/execute/status/{job_id}`) and file endpoints, and runs the autonomous `app.judge` evaluation loop with zero GCP credentials.

## Key Features & Infrastructure

- **Agent Substrate (`v1.0.0`) & Golden Snapshot**: An **ActorTemplate** (`judge-sandbox`) checkpoints a pre-initialized gVisor **Golden Snapshot** (`SNAPSHOT_FIDELITY_MEMORY`). Each evaluation spawns a fresh ephemeral **Judge Actor** from that Golden Snapshot on the `judge-workerpool` **WorkerPool** and deletes it immediately after grading.
- **Zero-Credential Sandboxing & Model Proxy**: Judge Actors hold no Google Cloud credentials and cannot reach the GKE metadata server. A per-actor **EgressPolicy** restricts outbound traffic to public HTTPS (`:443`) for cloning repositories and installing packages, plus HTTP to the Judge Orchestrator's **Model Proxy** (`http://agent.hackathon-judge.svc.cluster.local:8000/vertex-proxy`), which validates strict `generateContent` / `streamGenerateContent` paths and attaches the orchestrator's Workload Identity token for **Gemini Enterprise Agent Platform**.
- **Google Kubernetes Engine (GKE)**: Runs on a GKE Standard cluster with gVisor sandbox nodes (`--sandbox="type=gvisor"`) and Workload Identity.
- **Event-Driven Architecture & BigQuery**: Uses Google Cloud Pub/Sub to decouple the REST API from evaluation runs and Google Cloud BigQuery as the analytical data warehouse.
