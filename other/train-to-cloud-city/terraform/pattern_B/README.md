# Provisioning Cloud Firestore and Cloud Run

### Requirements

* `gcloud` cli (To install [click here](https://cloud.google.com/sdk/docs/install))
* `terraform` cli (To install [click here](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli))
* Google Cloud Platform project (To create a project [click here](https://cloud.google.com/resource-manager/docs/creating-managing-projects#gcloud))

## Technologies

* [Cloud Firestore](https://firebase.google.com/docs/firestore)
* [Cloud Run](https://cloud.google.com/run)
* [Cloud Build](https://cloud.google.com/build)
* [Artifact Registry](https://cloud.google.com/artifact-registry)

## Instructions

1. Login to Google Cloud Platform:

```bash
gcloud auth application-default login
```

2. Set current Google Cloud project:

```bash
gcloud config set project <project-id>
```

3. Point to test app in this directory and create a new Docker image with Cloud Build and push up new image to Artifact Registry

```bash
cd node-server/

gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/<project-id>/test-repo/image:tag1 .
```

4. Deploy your web client!

```bash
gcloud run deploy test-service --image us-central1-docker.pkg.dev/<project-id>/test-repo/image:tag1
```

5. *Result*: Open provided Cloud Run url to see client populate with the seeded data from Cloud Firestore.

## What's next?

* Learn more about [Firestore events to GKE via Eventarc triggers](https://cloud.google.com/eventarc/docs/gke/route-trigger-cloud-firestore)
* Learn more about [Firestore events to Cloud Run via Eventarc triggers](https://cloud.google.com/eventarc/docs/run/route-trigger-cloud-firestore)
* Learn more [Firestore events to Workflows via Eventarc triggers](https://cloud.google.com/eventarc/docs/workflows/route-trigger-cloud-firestore)
