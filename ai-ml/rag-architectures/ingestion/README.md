# Ingestion Function 

This Python function ingests raw text data from Cloud Storage, converts it to JSONL-style text embeddings, then uploads the embeddings to a Vertex AI Vector Search Index.

### Sample Data

The `wikipedia-data/` directory contains a sample dataset of 13 Wikipedia articles related to Quantum Computing. These articles were downloaded in February 2025. All Wikipedia text was licensed under the Creative Commons Attribution-ShareAlike 4.0 License ([src](https://en.wikipedia.org/wiki/Wikipedia:Text_of_the_Creative_Commons_Attribution-ShareAlike_4.0_International_License)), which allows for sharing and adaptation, with attribution.

### Environment Variables [Required]

```
export PROJECT_ID=<project-id>
export GCP_REGION=<region>
export VECTOR_SEARCH_INDEX_ID=<index-id>
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=<deployed-index-id>
export VECTOR_SEARCH_INDEX_ENDPOINT_NAME=<index-endpoint-name>
```

### Cloud Run Functions - IAM Roles needed for service account

- Vertex AI User 
- Storage Object User 


### Build and push image to Artifact Registry 

```
export ARTIFACT_REGISTRY_HOST=us-central1-docker.pkg.dev
export AR_REPOSITORY=gcf-artifacts/ingestion
export PROJECT_ID=next25rag
export IMAGE_TAG=latest 

export URL=$ARTIFACT_REGISTRY_HOST/$PROJECT_ID/$AR_REPOSITORY/$IMAGE_TAG
docker build --platform linux/amd64 -t $URL .
docker push $URL 
```