# Compute Engine with Node.js

### Requirements

- `gcloud` cli (To install [click here](https://cloud.google.com/sdk/docs/install))
- `terraform` cli (To install [click here](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli))
- Google Cloud Platform project (To create a project [click here](https://cloud.google.com/resource-manager/docs/creating-managing-projects#gcloud))

## Technologies

- [Compute Engine](https://cloud.google.com/compute)
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

3. Initialize and apply terraform like so:

```bash
terraform init  // Initializes and installs all required modules
terraform plan  // Displays preview of resources being applied to project
terraform apply // Executes application of resources
```

4. Open up node provisioned [virtual machine `node-virtual-machine`](https://console.cloud.google.com/compute/instances)

5. click `SSH` option of `node-virtual-machine` vm instance.

6. Inside the vm instance:

```bash
touch server.js // create app.js and copy contents of this directory's `./app.js`
node server.js // run server at port 5000
```

Continue to have the server running when you continue to the next step.

7. Execute the following in Cloud Shell to see the server response through an external url from Compute engine.

```bash
curl "$(terraform output --raw external-url)"
```

8. Clean up terraform resources by executing:

```bash
terraform destroy
```
