# Terraform for Party Game

## Requirements

* A blank Google Cloud Project
* [gcloud](https://cloud.google.com/sdk/docs/install) installed locally
* [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) installed locally

## Steps to deploy

* Copy [terraform.tfvars.sample](terraform.tfvars.sample) to your own terraform.tfvars and fill in. 

Then run in a shell:

```shell
gcloud auth application-default login 
terraform init
terraform apply
```