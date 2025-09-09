# BigQuery Data Preparation and BQML Demo

This repository contains the source code for a demonstration of a low-code AI pipeline within Google Cloud's BigQuery. The demo showcases how to take a raw CSV file with complex JSON strings, prepare the data using BigQuery's data preparation tools, generate vector embeddings with BigQuery ML (BQML), and use those embeddings to power a similarity search application.

This demo is the subject of a Google Codelab, which can be found here: [Effortless Data Prep in BigQuery: A Low-Coder's Guide](https://codelabs.developers.google.com/bq-dataprep)

## About this demo

This demo includes:

*   A frontend application (in the `frontend` directory) that provides a UI for searching for artwork and viewing similar pieces.
*   A backend server (in the `backend` directory) that queries BigQuery to find similar artwork based on vector embeddings.
*   A sample CSV file (`dataprep-met-bqml.csv`) containing data about artwork from the Metropolitan Museum of Art.

## Running the Demo

This demo is intended to be run within Google Cloud Shell to simplify authentication. While it can be run in a local environment, doing so will require additional steps to authenticate with Google Cloud.

### 1. Set up your environment in Cloud Shell

First, follow the setup and data preparation instructions in the [codelab](https://codelabs.developers.google.com/bq-dataprep). This will guide you through setting up your BigQuery dataset, creating a BQML remote model, and generating the necessary vector embeddings.

Once the data is prepared, run the following commands in your Cloud Shell terminal to set environment variables and copy required image data:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export BIGQUERY_DATASET=met_art_dataset
export REGION='us-central1'
bq cp bigquery-public-data:the_met.images $PROJECT_ID:met_art_dataset.images
```

### 2. Run the backend server

In your Cloud Shell terminal, start the backend server:

```bash
cd backend
npm install
node server.js
```

### 3. Run the frontend application

Open a new Cloud Shell tab by clicking the '+' icon. In the new tab, run the following commands to start the frontend:

```bash
cd frontend
npm install
npm run dev
```

### 4. Preview the application

Once the frontend server is running, click the "Web Preview" icon in the Cloud Shell toolbar and select "Preview on port 5173". This will open the application in a new browser tab.
