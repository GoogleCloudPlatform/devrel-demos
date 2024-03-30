# Basic CI/CD pattern

### Requirements

- `gcloud` cli (To install [click here](https://cloud.google.com/sdk/docs/install))
- `terraform` cli (To install [click here](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli))
- Google Cloud Platform project (To create a project [click here](https://cloud.google.com/resource-manager/docs/creating-managing-projects#gcloud))

## Technologies

- [Cloud Run](https://cloud.google.com/run)
- [Cloud Build](https://cloud.google.com/build)
- [Cloud Deploy](https://cloud.google.com/deploy)
- [Artifact Registry](https://cloud.google.com/artifact-registry)
- [Terraform](https://registry.terraform.io)

## Instructions

1. Login to Google Cloud Platform:

```bash
gcloud auth application-default login
```

2. Set current Google Cloud project:

```bash
gcloud config set project <project-id>
```

3. Navigate to Cloud Build page to [connect your repository](https://console.cloud.google.com/cloud-build/repositories/1st-gen) in global region.

4. Initialize and apply terraform like so.

```bash
terraform init  // Initializes and installs all required modules
terraform plan  // Displays preview of resources being applied to project
terraform apply // Executes application of resources
```

5. Once your set up is complete, you can test it by doing the following:
   a. Add new `target/` directory in your connected repository. This should contain code with relevant `cloudbuild.yaml` or `Dockerfile`.
   b. Pushing a test commit inside `target/` in your connected repository.
   c. Watch the build in Cloud Build complete pushing an image to Artifact Registry.
   d. Watch completion of push in Artifact Registry triggers `gcr` topic for Cloud Deploy to commence.

6. Clean up terraform resources by executing:

```bash
terraform destroy
```

## What's next?

- Try out walkthrough using Cloud Deploy with Cloud Run [![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/?show=ide%2Cterminal&walkthrough_id=deploy--cloud-deploy-e2e-run)
- Try out walkthrough using Cloud Deploy with GKE [![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/?show=ide%2Cterminal&walkthrough_id=deploy--cloud-deploy-e2e-gke)
