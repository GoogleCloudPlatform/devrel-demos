# Serving Backend 

This directory contains the source code and Dockerfile for the Cloud Run serving Backend. The backend is a FastAPI server that takes the user's Quantum Computing question from the frontend, and performs a RAG-based search using Vertex AI Vector Search and Gemini 2.0 Flash (Vertex AI). 

### Env Variables (Required)

```
export PROJECT_ID=<PROJECT_ID>
export GCP_LOCATION=<GCP_LOCATION>
export VECTOR_SEARCH_INDEX_ID=<VECTOR_SEARCH_INDEX_ID>
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=<VECTOR_SEARCH_DEPLOYED_INDEX_ID>
export VECTOR_SEARCH_INDEX_ENDPOINT_NAME=<VECTOR_SEARCH_INDEX_ENDPOINT_NAME>
export GEMINI_MODEL_NAME=gemini-2.0-flash-001 #substitute model of your choice
```

### Testing Locally 

```
python3 app.py
```

#### Example `curl` requests 

Note that the `use_context` flag is defaulted to `true` - when set to `false`, the prompt will be passed directly to the Gemini API without augmenting via Vertex AI Search. 

```
 curl -X POST "http://localhost:8000/prompt" \
     -H "Content-Type: application/json" \
     -d '{
         "prompt": "What is Majorana 1?",
         "num_neighbors": 3,
         "use_context": true
     }'

 curl -X POST "http://localhost:8000/prompt" \
     -H "Content-Type: application/json" \
     -d '{
         "prompt": "What is Majorana 1?",
         "num_neighbors": 3,
         "use_context": false
     }'
```

### Cloud Run service account - Required IAM Roles

- Vertex AI User 
