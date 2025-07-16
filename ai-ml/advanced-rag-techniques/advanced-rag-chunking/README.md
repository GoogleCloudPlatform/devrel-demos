# Advanced RAG Techniques - Chunking

This code sample shows the end-state of the code created in this Advanced RAG Techniques - Chunking lab. (TKTK: add link to lab when published)

Author: [Amit Maraj](https://github.com/amitkmaraj)

## Overview

This lab guides you through building a Retrieval Augmented Generation (RAG) application using Google Cloud's [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres) (with the pgvector extension) and a Gemini Large Language Model (LLM) via [Vertex AI](https://cloud.google.com/vertex-ai/docs). You will set up a vector database, ingest data using different text chunking strategies, generate embeddings, and create a retrieval mechanism to query a sample dataset, observing how chunking impacts results.

## Getting Started

### Install Requirements

You'll want to install the requirements to get started. 

```bash
pip3 install -r requirements.txt
```

### Defining values in the `.env` file

You will need to define the following values in the `.env` file: 
- `REGION`
- `PROJECT_ID`
- `SQL_PASSWORD`