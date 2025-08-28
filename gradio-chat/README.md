# Gradio-Based AI Chat App on GKE


This repository deploys the gemma3-12b-it model and a gradio-based ai chat app to a GKE cluster (which is set up via terraform). The chat app can switch between chatting with the GKE-deployed Gemma3-12b-it model, and Gemini-2.5-flash in Vertex AI. The application stores each session's chat history, and the history is shared even if you switch which model you're chatting with (Gemini or Gemma2).


![This screenshot shows the chat application.](screenshots/UI_Screenshot.png "AI Chat Application Screenshot")

## Pre-Reqs
You should have:
* a [Hugging Face token](https://huggingface.co/docs/hub/en/security-tokens).
* a [Google Cloud project](https://developers.google.com/workspace/guides/create-project) with billing enabled.
* [Terraform installed](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) on the machine you will deploy from.
* The [gcloud CLI installed](https://cloud.google.com/sdk/docs/install) on the machine you will deploy from.

## Running this application
Clone this application code onto the machine you will deploy from. Navigate to the directory you cloned the files into.

If it's not already set, set your working project for the gcloud cli. Replace [YOUR_PROJECT_ID] with your project id.
```
gcloud config set project [YOUR_PROJECT_ID]
```

Create environment variables to set the project you will deploy to via Terraform.
```
export TF_VAR_project_id=$(gcloud config get-value project)
export TF_VAR_project_number=$(gcloud projects describe $TF_VAR_project_id --format="value(projectNumber)")
```

These environment variables will automatically be used by terraform. They are also needed to replace placeholder text in the chat-deploy.yaml and skaffold.yaml files. Do this now:
```
sed -i -e 's|\[PROJECT-ID]|'"$TF_VAR_project_id"'|g' build/chat-deploy.yaml
sed -i -e 's|\[PROJECT-ID]|'"$TF_VAR_project_id"'|g' build/skaffold.yaml
```

### Enable APIs
Enable the needed APIs via the gcloud CLI by running the command:
```
gcloud services enable cloudbuild.googleapis.com artifactregistry.googleapis.com container.googleapis.com firestore.googleapis.com aiplatform.googleapis.com
```


### Create the Google Cloud resources using terraform

The main.tf file in this project contains code to enable APIs for Google Cloud Build, Artifact Registry, Firestore, VertexAI, and GKE.
It will create the following resources in region us-central1:
* A GKE autopilot cluster named "gradio-chat-cluster"
* A Firestore collection called "chat_sessions", with an initial document, "session1"

The GKE cluster will be used to run the Gemma model instance, and the gradio-based chat application.
The Firestore collection will be used to store chat history.

1. Change directories into the "infra" folder within this repository.
```
cd infra
```

2. Initialize Terraform:
```
terraform init
```

3. Check what resources Terraform will create:
```
terraform plan
```

4. Create the resources using Terraform:
```
terraform apply
```

### Connect to the cluster from your local machine
Once the cluster has finished deploying, connect to the cluster from your local machine.
```
gcloud container clusters get-credentials gradio-chat-cluster --region us-central1 --project $TF_VAR_project_id
```

Change directories to the home directory where you cloned this code.
```
cd ..
```

### Deploy Gemma
This repo deploys Gemma3-12b-it from Hugging Face, as a Deployment on the GKE Autopilot cluster. 

1. Set your Hugging Face token as an environment variable
```
export hf_token=[YOUR_HF_TOKEN]
```

2. Set your Hugging Face token as a Kubernetes Secret
NOTE: Kubernetes secrets obfuscate secret data, but do not encrypt them! For use in production or shared environments, store your hugging face token in a more secure tool such as Google Cloud Secrets Manager. If you change this, you will need to update gemma3-12b-deployment.yaml to use the secret wherever it is stored.
```
kubectl create secret generic hf-secret --from-literal=hf_api_token="$hf_token"
```

3. Deploy Gemma3-12b-it as a workload on the GKE Autopilot cluster:
```
kubectl apply -f build/gemma3-12b-deploy.yaml
```

### Deploy the chat app
This repo is designed to build the chat application container image using Google Cloud Build. The image is stored in Artifact Registry, and then can be deployed to the GKE cluster using the chat-deploy.yaml file.

NOTE: Rather than doing this, you could open the code in VS Code and use the [Cloud Code plugin](https://cloud.google.com/code/docs/vscode/install) to run and deploy it. This works great, and is convenient if you want to explore and edit this application!

#### Build and Run the application using Skaffold and Google Cloud Build
This repo is designed to be built using Google Cloud Build via Skaffold. Skaffold simplifies the build and deploy process by automating the pipeline from building on CloudBuild to deploying onto the GKE cluster.
```
skaffold run -f build/skaffold.yaml
```

Note: When a container image of the application is built, it uses the "latest" flag. If this app were to be used in production, you should design the CI/CD workflow to flag each container image with major and minor versions as a best practice.

#### Configure Workload Identity
This application relies on Workload Identity to enable the workloads running within the GKE cluster to access Firestore and VertexAI. Workload Identity allows you to configure a Kubernetes Service Account as a principal, and assign it roles/rolebindings through Google Cloud IAM.


You created the Kubernetes Service Account (gradio-chat-ksa) when you deployed the chat application, but the application will not work until you create rolebindings for that Kuberentes Service Account via Workload Identity.


1. Give the Kubernetes Service Account the "iam.serviceAccountTokenCreator" role. This allows the workload to create the token it needs to interact with other Google Cloud services.
```
gcloud projects add-iam-policy-binding projects/"$TF_VAR_project_id" \
    --role=roles/iam.serviceAccountTokenCreator \
    --member="principal://iam.googleapis.com/projects/$TF_VAR_project_number/locations/global/workloadIdentityPools/$TF_VAR_project_id.svc.id.goog/subject/ns/default/sa/gradio-chat-ksa"
```

2. Give the Kubernetes Service Account the "aiplatform.user" role. This allows the workload to interact with VertexAI.
```
gcloud projects add-iam-policy-binding projects/"$TF_VAR_project_id" \
    --role="roles/aiplatform.user" \
    --member="principal://iam.googleapis.com/projects/$TF_VAR_project_number/locations/global/workloadIdentityPools/$TF_VAR_project_id.svc.id.goog/subject/ns/default/sa/gradio-chat-ksa"
```
3. Give the Kubernetes Service Account the "datastore.user" role. This allows the workload to interact with Firestore.
```
gcloud projects add-iam-policy-binding projects/"$TF_VAR_project_id" \
    --role="roles/datastore.user" \
    --member="principal://iam.googleapis.com/projects/$TF_VAR_project_number/locations/global/workloadIdentityPools/$TF_VAR_project_id.svc.id.goog/subject/ns/default/sa/gradio-chat-ksa"
```

#### Access the application
Once the application has deployed and your rolebindings are set, you can access the application on the external IP (via Loadbalancer). The application is served on port 7860.

1. Get the External IP using kubectl
```
kubectl get svc
```

2. Connect to the external IP, with the port 7860. ie: 0.0.0.0:7860

The application will take a couple minutes to become available.

Enjoy chatting with Gemini and Gemma2!

## Log Example
This application logs each session as a document in Firestore. The document name is in the format "year-month-day-session-uuid". Here is an example of a log for a single session.

![This screenshot shows an example chat session log as stored in a Firestore document.](screenshots/ExampleLog.png "Log Example Screenshot")