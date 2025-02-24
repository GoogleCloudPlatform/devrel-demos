# Next '25 Breakout: From AWS to Google Cloud - Expand Your Cloud Toolkit 

This demo shows how to migrate an AWS application, hosted on Elastic Kubernetes Service (EKS) and Relational Database Service (RDS), to Google Cloud Platform (GCP) using Google Kubernetes Engine (GKE) and Cloud SQL (via Database Migration Service).

We use the CymbalBank (Bank of Anthos) sample application to demonstrate the migration.

To deploy this demo on Google Cloud, you need:

- A [Google Cloud project](https://cloud.google.com/docs/overview#projects) with
  billing enabled. We recommend to deploy this reference architecture an a new,
  dedicated Google Cloud project.
- An account with the Project Owner (`roles/owner`) role.

## Deploy Google Cloud infrastructure

1. Open [Cloud Shell](https://cloud.google.com/shell).

1. Clone this repository and change the working directory:

   ```bash
   git clone https://github.com/askmeegs/devrel-demos.git && \
   cd devrel-demos && \
   git switch next25-aws-gcp-migration
   ```

1. Set the default Google Cloud project:

  ```bash
  gcloud config set project "<GOOGLE_CLOUD_PROJECT_ID>"
  ```

  - `<GOOGLE_CLOUD_PROJECT_ID>` is the ID of the Google Cloud project where you
    want to provision the resources for this demo.


1. Provision the infrastructure on Google Cloud

  ```bash
  GOOGLE_CLOUD_PROJECT_ID="<GOOGLE_CLOUD_PROJECT_ID>" containers/aws-gcp-migration/google-cloud-infra-deploy.sh
  ```

  Where:

  - `<GOOGLE_CLOUD_PROJECT_ID>` is the ID of the Google Cloud project where you
    want to provision the resources for this demo.
