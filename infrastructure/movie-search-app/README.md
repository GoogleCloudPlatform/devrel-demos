
# Sample app for genai embeddings using Pinecone or PostgreSQL compaible database
## Description
- The demo shows a sample movie search chat assistant using either Pinecone or PostgreSQL compatible database as a backend. 
- In both cases the Google AI studio is used for conversations and embedding generation.

### Architecture
- The application can be deployed on a VM or any other environment supporting Python 3.11
- It connects to a Pinecone environment using Pinecone API token
- It uses Google AI Studio to generate responses (using model gemini-1.5-flash) or to generate embeddings (model textetext-embedding-004)

## Requirements
- Platform to deploy the application supporting Python 3.11
- Token in Google AI studio (you can get it from [here](https://ai.google.dev/gemini-api/docs/api-key))
- Token for Pinecone API (optional)
- Project in Google Cloud with enabled APIs for all components.


## Deployment for Pinecone Backend

The dataset with movies and how to deploy it to the Pinecone environment is not discussed here.

### Prepare Virtual machine
- Enable the required APIs in Google Cloud
```
gcloud services enable compute.googleapis.com
```
- Create a GCE VM in a Google Cloud project
- Connect to the VM ussing SSH
- Clone the software 
```
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
```
- Prepare Python 3.11 
```
sudo apt install -y python3.11-venv git
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```
### Run the application
- Change directory
```
cd devrel-demos/infrastructure/movie-search-app
```
- Install dependencies
```
pip install -r requirements.txt
```
- Set environment variables (Pinecone index name)
```
export PINECONE_INDEX_NAME=netflix-index-01
export PORT=8080
```
- Start the application from command line
```
gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 movie_search:me
```
- Connect to the chat using the VM host:port to get the application interface

### Work with application
- Click at the bottom of the app to choose backend.
- Put Google AI API token and Pinecone API token at the top (you need both to use the Pinecone backend).
- Select Pinecone as a backend and confirm the choice.
- Post your question in the input window at the bottom and click the arrow.

Ask sample questions about the movies

### You can deploy your application to Cloud Run
Optionally you can deploy the application to Cloud Run. 

## Deployment with AlloyDB Backend
You will need AlloyDB database as a backend for the application.

Assuming all the actions are performed in the same Google Cloud project.
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
                       iam.googleapis.com
```

### Create AlloyDB cluster
Please follow instruction in the documentation to create an AlloyDB cluster and primary instance in the same project where the application is going to be deployed.

Here is the [link to the documentation for AlloyDB](https://cloud.google.com/alloydb/docs/quickstart/create-and-connect)

### Create a database in AlloyDB
Create a database with the name movies and the user movies_owner. You can choose your own names for the database and the user. The application takes it from environment variables. Optionally you can modify the application to use secret manager in Google Cloud as more secured approach.

### Migrate data from Pinecone to AlloyDB
- Move the data from Pinecone to AlloyDB

### Enable virtual environment for Python
You can use either your laptop or a virtual machnie for deployment. Using a VM deployed in the same Google Cloud project simplifies deployeent and network configuration. On a Debian Linux you can enable it in the shell using the following command:
```
sudo apt-get update
sudo apt install python3.11-venv git postgresql-client
python3 -m venv venv
source venv/bin/activate
```

### Clone the software
Clone the software using git:
```
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
```
### Run the application
- Change directory
```
cd devrel-demos/infrastructure/movie-search-app
```
- Install dependencies
```
pip install -r requirements.txt
```
- Here are the environment variables used by the application
```
export PINECONE_INDEX_NAME=netflix-index-01
export PORT=8080
export DB_USER=movies_owner
export DB_PASS=DatabasePassword
export DB_NAME=movies
export INSTANCE_HOST=ALLOYDB_IP
export DB_PORT=5432
```
- Here is the command used to start the application

```
gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 movie_search:me
```
- Connect to the chat using the VM host:port to get the application interface

### Deploy the applicaion to Cloud Run
Create a service account movie-search-identity and grant role VertexAI User to the account - optional now since we are not using Vertex AI as of now.
Build and deploy application to the Cloud Run service.
The environment variables values should be replaced by the database owner, password, database name and the AlloyDB IP

```
gcloud alpha run deploy movie-search-app \
   --source=./ \
   --no-allow-unauthenticated \
   --service-account movie-search-identity \
   --region us-central1 \
   --network=default \
   --set-env-vars=DB_USER=movies_owner,DB_PASS=StrongPassword,DB_NAME=movies,INSTANCE_HOST=127.0.0.1,DB_PORT=5432 \
   --quiet
```
### Work with application
- Click at the bottom of the app to choose backend.
- Put Google AI API token and Pinecone API token at the top (you need both to use the Pinecone backend).
- Select Pinecone as a backend and confirm the choice.
- Post your question in the input window at the bottom and click the arrow.

Ask sample questions about the movies

# TO DO
- Add support for other models and providers

# License
Apache License Version 2.0; 
Copyright 2024 Google LLC


