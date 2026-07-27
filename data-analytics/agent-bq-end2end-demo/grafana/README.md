# Vegas Navigator: Local Grafana Real-Time Dashboard Setup

This directory contains the stateless configuration required to start a local instance of Grafana with the official Google BigQuery connector. This setup is configured for local development and contains a pre-provisioned real-time sentiment analytics dashboard.

---

## Architecture & Sourcing

*   **Grafana Container**: Sourced from the official Docker Hub open-source image: `grafana/grafana-oss:latest`.
*   **Custom Build**: We build a custom Docker image using our local `Dockerfile` to pre-install the Google Cloud CLI (`gcloud`) inside the container. This eliminates any dependency on local host filesystem gcloud paths.
*   **BigQuery Datasource**: Programmatically provisions the official `grafana-bigquery-datasource` plugin.
*   **Keyless Authentication**: Bypasses the need for Service Account JSON key files on disk. Instead, you authenticate directly inside the running container to generate Application Default Credentials (ADC).

---

## Prerequisites

Ensure you have one of the following container runtimes running on your Mac:
*   **Colima (Recommended)**: Verify it is installed and started (`colima start`).
*   **Docker Desktop**: Verify the daemon is active.

---

## Step-by-Step Setup

Follow these steps to start Grafana, log in inside the container, and load the real-time sentiment dashboard.

### Step 1: Configure Environment Variables
Ensure you have your target Google Cloud Project ID set in your active terminal:
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
```
*(Optional)* You can also configure a custom port or admin password (defaults to port `3000` and password `admin`):
```bash
export GRAFANA_PORT=3000
export GRAFANA_ADMIN_PASSWORD="your-secure-password"
```

### Step 2: Build and Start the Stack
Run the startup script from the root of this folder:
```bash
./start_grafana.sh
```
This script will:
1.  Check for an active Docker daemon. If the daemon is inactive and Colima is installed, it automatically runs `colima start`.
2.  Build your custom Grafana image with pre-installed `gcloud` tools.
3.  Deploy the container and map the BigQuery datasource and sentiment dashboard configurations.

### Step 3: Authenticate Inside the Container
Once the container is running, execute this interactive command to login inside the container:
```bash
docker exec -it local-grafana-bigquery gcloud auth application-default login
```

#### What happens during authentication:
1.  The container launches the interactive Google OAuth CLI workflow.
2.  It prints an authorization URL in your terminal.
3.  Copy and paste the URL into your web browser, log in with your Google Cloud account, and grant access.
4.  Copy the authorization code from the browser and paste it back into your terminal prompt inside the container.
5.  The container writes the credentials directly to `/home/grafana/.config/gcloud/application_default_credentials.json` which the Grafana process inherits.

---

## Viewing the Dashboard

1.  Open your web browser and navigate to: `http://localhost:3000` (or your configured `$GRAFANA_PORT`).
2.  Log in using the credentials:
    *   **Username**: `admin`
    *   **Password**: `admin` (or your configured `$GRAFANA_ADMIN_PASSWORD`).
3.  Navigate to Dashboards inside the Grafana sidebar.
4.  Open the Vegas Navigator Real-Time Observability dashboard.

---

## What is Pre-Configured?

The provisioning setups automatically configure the following:

### 1. Datasource Connection (`provisioning/datasources/bigquery.yaml`)
Automatically connects to your Google Cloud Project without storing credentials or JSON key files in your codebase or host disk.

### 2. Live Monitoring Panels (`provisioning/dashboards/sentiment_dashboard.json`)
*   **Total Interactions Evaluated**: Displays a rolling count of all user entries processed.
*   **Real-Time User Sentiment Polarity Trend**: Renders a time-series line graph showing rolling user sentiment scores (scaled between `-1.0` and `+1.0`). Uses conditional threshold colors (Red for frustration, Yellow for neutral, Green for delight).
*   **Top Extracted Entities & Location Highlights**: Renders a bar chart aggregating top extracted locations, hotel entities, and keywords from your nested telemetry events array to identify trending user inquiries.
