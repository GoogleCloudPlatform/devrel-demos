
# Cymbal toystore demo
## Requirements
- Project in Google Cloud with enabled APIs for all components.
- AlloyDB cluster and primary instance created 
- A laptop or a VM with Python 3.11+,git and postggres utilities such as psql

### Clone the software
Clone the software using git:
```
git clone https://github.com/gotochkin/devrel-demos.git
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
                       iam.googleapis.com
```

### Create AlloyDB cluster
Please follow instruction in the documentation to create an AlloyDB cluster and primary instance in the same project where the application is going to be deployed.

Here is the [link to the documentation for AlloyDB](https://cloud.google.com/alloydb/docs/quickstart/create-and-connect)
For example after creating the instance you get:
- Cluster name:my-cluster
- Instance name:my-instance
- Instance IP:10.3.141.2
- Postgres user:postgres
- Postgres password:StrongPassword

### Enable virtual environment for Python
You can use either your laptop or a virtual machnie for deployment. I am using a VM deployed in the same Google pCloud project. On a Debian Linux you can enable it in the shell using the following command:
```
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
Create a database with the name cymbal_store and the user cymbal
```
export PGPASSWORD=StrongPassword
psql "host=10.3.141.2 user=postgres dbname=postgres" -c "create database cymbal_store"
psql "host=10.3.141.2 user=postgres dbname=postgres" -c "create user cymbal with password 'StrongPassword'"
psql "host=10.3.141.2 user=postgres dbname=postgres" -c "GRANT ALL ON DATABASE cymbal_store to cymbal;"
psql "host=10.3.141.2 user=postgres dbname=cymbal_store" -c "GRANT ALL ON SCHEMA public TO cymbal;"
psql "host=10.3.141.2 user=postgres dbname=cymbal_store" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql "host=10.3.141.2 user=postgres dbname=cymbal_store" -c "CREATE EXTENSION IF NOT EXISTS google_ml_integration;"
```
Load the data
```
cd ~/devrel-demos/infrastructure/cymbal-toy-store/data/
psql "host=10.3.141.2 user=cymbal dbname=cymbal_store" <cymbal_toystore.sql
```

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


