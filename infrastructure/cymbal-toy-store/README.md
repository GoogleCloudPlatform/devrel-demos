
# Cymbal toystore demo
## Requirements

## Deployment
### Deploy in Cloud Run 
* Switch to the directory 
* Create configuration file
* Deploy the application to Cloud rRun 
```
gcloud alpha run deploy cymbal-toystore \
   --source=./ \
   --no-allow-unauthenticated \
   --service-account cymbal-shop-identity \
   --region us-central1 \
   --network=default \
   --quiet
   ```

* Get endpoint 

# Licence

Apache License Version 2.0; 
Copyright 2024 Google LLC

