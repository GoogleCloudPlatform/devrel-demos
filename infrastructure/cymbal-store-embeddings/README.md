
# Sample app for genai embeddings
## Description
- The demo shows a sample retail chat assistant using a postgres compatible database to offer a product from the inventory based on the question asked.

### Architecture


## Requirements
- Platform to deploy the application supporting Python 3.11
- Token in Google AI studio
- Token for OpenAI API (optional)
- Project in Google Cloud with enabled APIs for all components.

### Clone the software
Clone the software using git:
```
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
```



## Deployment
### Enable all required APIs usng gcloud command
```
gcloud services enable alloydb.googleapis.com \
                       compute.googleapis.com \
                       cloudresourcemanager.googleapis.com \
                       servicenetworking.googleapis.com \
                       vpcaccess.googleapis.com \
                       aiplatform.googleapis.com \
                       cloudbuild.googleapis.com \
                       artifactregistry.googleapis.com \
                       run.googleapis.com \
                       iam.googleapis.com \
                       secretmanager.googleapis.com
```

### Create AlloyDB cluster
Please follow instruction in the documentation to create an AlloyDB cluster and primary instance in the same project where the application is going to be deployed.

Here is the [link to the documentation for AlloyDB](https://cloud.google.com/alloydb/docs/quickstart/create-and-connect)
For example after creating the instance you get:


### Enable virtual environment for Python
You can use either your laptop or a virtual machnie for deployment. I am using a VM deployed in the same Google pCloud project. On a Debian Linux you can enable it in the shell using the following command:
```
sudo apt-get update
sudo apt install python3.11-venv git postgresql-client
python3 -m venv venv
source venv/bin/activate
```

### Clone the software
Clone the software using git:
```
git clone https://github.com/gotochkin/devrel-demos.git
```

### Load the data
```
cd devrel-demos/infrastructure/cymbal-store-embeddings
```
Create a database with the name cymbal_store and the user cymbal


Calculate the embeddings

### Run the application 
```
gunicorn --bind :8080 --reload --workers 1 --threads 8 --timeout 0 cymbal_store:me
```

### Deploy the applicaion to Cloud Run


* Requests to Try 
  - Ask in the chat - "What kind of fruit trees grow well here?"

# License
Apache License Version 2.0; 
Copyright 2024 Google LLC

