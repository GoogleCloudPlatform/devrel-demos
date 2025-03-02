# Ingestion Function 

### Env variables needed (Cloud Run)

```
export PROJECT_ID=next25rag
export GCP_REGION=us-central1
export GCS_BUCKET=ingest-67ab
export INPUT_DOC_FILENAME=majorana1.txt
export VECTOR_SEARCH_INDEX_ID=4890482584812781568
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=megan_text_index_endpoint2_1740675419602
export VECTOR_SEARCH_INDEX_ENDPOINT_NAME="projects/427092883710/locations/us-central1/indexEndpoints/5070556201163423744"
```

### CRF IAM Permissions Needed 

Service account: `function-service-account-67ab@next25rag.iam.gserviceaccount.com` 

- Vertex AI User 
- Storage Object User 