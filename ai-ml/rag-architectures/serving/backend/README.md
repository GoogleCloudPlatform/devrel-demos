# FastAPI Backend 


### Env vars needed

```
export PROJECT_ID=next25rag
export GCP_LOCATION=us-central1
export VECTOR_SEARCH_INDEX_ID=4890482584812781568
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=megan_text_index_endpoint2_1740675419602
export VECTOR_SEARCH_INDEX_ENDPOINT_NAME="projects/427092883710/locations/us-central1/indexEndpoints/5070556201163423744"
export GEMINI_MODEL_NAME=gemini-2.0-flash-001
```


### Local testing 

```
python3 app.py
```


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