# Cymbal toystore demo
## Requirements
## Deployment
### Deploy in Cloud Run 
* Switch to the directory 
* Create configuration file
* Deploy the application to Cloud rRun 
```
gcloud alpha run deploy next2024-cymbal-toystore \
   --source=./ \
   --no-allow-unauthenticated \
   --service-account cymbal-shop-identity \
   --region us-central1 \
   --network=default \
   --quiet
   ```

* Get endpoint 
