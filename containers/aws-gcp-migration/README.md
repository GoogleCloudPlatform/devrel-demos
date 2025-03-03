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

  Where:

  - `<GOOGLE_CLOUD_PROJECT_ID>` is the ID of the Google Cloud project where you
    want to provision the resources for this demo.

1. Create a file at the
  `containers/aws-gcp-migration/dms-user-password-source-database.txt` path, and
  save the password of the database user that Database Migration Service uses to
  connect to the source database.

1. Provision the infrastructure on Google Cloud

  ```bash
  GOOGLE_CLOUD_PROJECT_ID="<GOOGLE_CLOUD_PROJECT_ID>" \
  SOURCE_DATABASE_HOSTNAME="<SOURCE_DATABASE_HOSTNAME>" \
  SOURCE_DATABASE_DMS_USERNAME="<SOURCE_DATABASE_DMS_USERNAME>" \
    containers/aws-gcp-migration/gcp/google-cloud-infra-deploy.sh
  ```

  Where:

  - `<GOOGLE_CLOUD_PROJECT_ID>` is the ID of the Google Cloud project where you
    want to provision the resources for this demo.
  - `<SOURCE_DATABASE_HOSTNAME>` is the hostname of the source database.
  - `<SOURCE_DATABASE_DMS_USERNAME>` is the username of the user that Database
    Migration Service uses to connect to the source database.

1. Start the
  [Database Migration Service migration job](https://console.cloud.google.com/dbmigration/migrations)
  from the Cloud Console.

### Limitations

- Database Migration Service doesn't migrate database users and user roles. For
  simplicity, we use only the `postgres` user through this migration, so you
  need to update the password of the `postgres` user in the destination Cloud
  SQL instance. For simplicity (again), we use the same password of the
  `postgres` user in the source Amazon RDS database. To change the `postgres`
  user password in the Cloud SQL instance, open Cloud Shell and run the
  following command:

    ```bash
    gcloud sql users set-password postgres --instance=acp-a-g-demo-dest --password=$(cat containers/aws-gcp-migration/dms-user-password-source-database.txt)
    ```


## Destroy Google Cloud infrastructure

1. Open [Cloud Shell](https://cloud.google.com/shell).

1. Provision the infrastructure on Google Cloud

  ```bash
  GOOGLE_CLOUD_PROJECT_ID="<GOOGLE_CLOUD_PROJECT_ID>" \
  SOURCE_DATABASE_HOSTNAME="<SOURCE_DATABASE_HOSTNAME>" \
  SOURCE_DATABASE_DMS_USERNAME="<SOURCE_DATABASE_DMS_USERNAME>" \
    containers/aws-gcp-migration//gcp/google-cloud-infra-teardown.sh
  ```

  Where:

  - `<GOOGLE_CLOUD_PROJECT_ID>` is the ID of the Google Cloud project where you
    want to provision the resources for this demo.
