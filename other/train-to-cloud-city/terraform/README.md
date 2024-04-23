# Google Cloud Patterns

### Requirements

- `gcloud` cli (To install [click here](https://cloud.google.com/sdk/docs/install))
- `terraform` cli (To install [click here](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli))
- Google Cloud Platform project (To create a project [click here](https://cloud.google.com/resource-manager/docs/creating-managing-projects#gcloud))

## Getting Started

1. Navigate to any of the following patterns directories:

   - [Mission A - Compute Engine with Node.js](./low_complexity/)
   - [Mission B - Provision Cloud Firestore with Cloud Run](./medium_complexity/)
   - [Mission D - CI/CD pipeline](./high_complexity/)

  Note: [Mission C - Host a database backed website](https://console.cloud.google.com/welcome?walkthrough_id=sql--mysql--quickstart-cloud-run) is a walkthrough. Try it out!

2. Apply Google Cloud resources with `terraform`:

   ```bash
   terraform init  // Initializes and installs all required modules
   terraform plan  // Displays preview of resources being applied to project
   terraform apply // Executes application of resources
   ```

To clean up, run `terraform destroy` to remove resources.
