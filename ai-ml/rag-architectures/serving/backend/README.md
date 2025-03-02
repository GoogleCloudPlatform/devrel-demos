# FastAPI Backend 


### Env vars needed

```
export GCP_PROJECT_ID=next25rag
export GCP_LOCATION=us-central1
export VECTOR_SEARCH_INDEX_ID=4890482584812781568
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=megan_text_index_endpoint2_1740675419602
export VECTOR_SEARCH_ENDPOINT_ID="projects/427092883710/locations/us-central1/indexEndpoints/5070556201163423744"
GEMINI_MODEL_NAME=gemini-2.0-flash-001
```


### Local testing 

```
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```