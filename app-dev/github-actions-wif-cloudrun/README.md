# Setting up Workload Identity Federation for Cloud Run services deployed with GitHub Actions

# Automatic

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fgooglecloudplatform%2Fdevrel-demos&cloudshell_tutorial=README.walkthrough.md&cloudshell_workspace=app-dev/github-actions-wif-cloudrun)


# Manual

In this tutorial, we'll configure a GitHub repo to use Workload Identity Federation to deploy a Cloud Run service whenever a merge happens on the default branch.

This tutorial is a combination of the following technologies: 

 * The [deploy-cloudrun](https://github.com/google-github-actions/deploy-cloudrun) GitHub action
 * Terraform, and the [`gh-oidc` Terraform module](https://github.com/terraform-google-modules/terraform-google-github-actions-runners)
 * [Source based Cloud Run deploys](https://cloud.google.com/run/docs/deploying-source-code)


## Things you will need

* A [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project), with billing enabled. 
  * [Create a new project](https://console.cloud.google.com/projectcreate) in the Google Cloud Console
* A [GitHub](https://github.com/) repo that contains the source code for the service you want to deploy. 
  * Your repo will need to have a Dockerfile, or use [Google Cloud Buildpacks](https://cloud.google.com/docs/buildpacks)
* The [`gcloud` CLI](https://cloud.google.com/sdk/gcloud)
  * [Installation instructions](https://cloud.google.com/sdk/docs/install) 
* The [`terraform` CLI](https://terraform.io)
  * [Installation instructions](https://developer.hashicorp.com/terraform/downloads)

ℹ️ Both `gcloud` and `terraform` come pre-installed these tools are available in the [Google Cloud Shell](https://console.cloud.google.com/home/dashboard?cloudshell=true) ([learn more](https://cloud.google.com/shell)).


## Steps


### Setup your project

1. Configure your `gcloud` CLI for the project: 
    ```bash
    export PROJECT_ID={Your Project ID}
    gcloud config set project $PROJECT_ID
    ```
1. Enable the Google Cloud APIs: 
    ```bash
    gcloud services enable \
        cloudresourcemanager.googleapis.com \
        cloudbuild.googleapis.com
    ```
1. Create a service account that will be used by Terraform, loading it into your Application Credentials:
    ```bash
    gcloud iam service-accounts create terraform-sa \
    --display-name "Terraform Service Account"
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member serviceAccount:terraform-sa@${PROJECT_ID}.iam.gserviceaccount.com \
        --role roles/owner
    gcloud iam service-accounts keys create ~/terraform-sa-key.json \
        --iam-account terraform-sa@${PROJECT_ID}.iam.gserviceaccount.com
    export GOOGLE_APPLICATION_CREDENTIALS=~/terraform-sa-key.json
    ```

### Create Workload Identity Federation elements

1. Create a new directory outside of your local git repo
   
   Note: this will prevent the Terraform file or associated output from ending up in your application code.
1. Copy the Terraform code in [`main.tf`](main.tf) to your working directory
1. Initialise and run the Terraform code: 
    ```bash
    export GITHUB_REPO={User/Repo}
    terraform init
    terraform apply \
        -var project_id=$PROJECT_ID \
        -var github_repo=$GITHUB_REPO
    ```

    Check the output, and type `yes` to confirm to Terraform to perform the actions. 
1. Note the outputted `auth` step, as this will be used later.

### Create the GitHub workflow

1. In your local git repo, create the github workflow `.github/workflows/source_deploy.yaml`, updating:
    * `DEFAULT_BRANCH` with the default branch for your repo (e.g. `main`),
    * `REGION`, your Google Cloud region (e.g. `us-central1`), 
    * `SERVICE`, the name you want to call your Cloud Run service, and
    * the `auth` step with output from Terraform:

    ```yaml
    name: source_deploy

    on:
      push:
        branches:
          - DEFAULT_BRANCH

    jobs:
      deploy:
        runs-on: ubuntu-latest
        permissions:
          contents: 'read'
          id-token: 'write'

        steps:
        - uses: actions/checkout@v3

        - id: 'auth'
        # Add output from Terraform

        - name: 'Deploy to Cloud Run'
          uses: 'google-github-actions/deploy-cloudrun@v0'
          with:
            source: '.'
            region: REGION
            service: SERVICE
    ```

1. Commit the `.github/workflows/source_deploy.yaml` file to your repo's main branch and push the change
    ```bash
    git add .github/workflows/source_deploy.yaml
    git commit -m "Add GitHub Action for deploy-cloudrun"
    git push
    ```
1. On the GitHub website, go to your repo and click the Actions tab.
1. Note the running action.

Your repo will now be deployed, initially as a private service. 

### Testing success

Your service will be deployed as a private service, so you will not be able to view it publicly, yet. 

1. Find the service URL through the `gcloud` cli: 
    ```bash
    gcloud run services list

    export SERVICE_URL=$(gcloud run services describe SERVICE --region REGION --format "value(status.url)")
    echo Service deployed to $SERVICE_URL
    ```
1. Use `curl` to GET the service, using your `gcloud` identity: 

    ```bash
    curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" $SERVICE_URL
    ```

1. If you want to make the service public, add the IAM to allow all users access: 
    ```
    gcloud run services add-iam-policy-binding \
        SERVICE --region REGION \
        --member allUsers --role roles/run.invoker 
    ```


# Notices

This sample is unmaintained. 