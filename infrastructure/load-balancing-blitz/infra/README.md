## Infra

Use Terraform for building basic infra resources in Google Cloud Platform.

## How to?

* (Preferred) Use Cloud Shell editor for deploying this APP. Cloud Shell editor has preinstalled `terraform` tool
* (Setup/ Libraries) Run `terraform init` in `/infra` folder. This download necessary libraries for Terraform.
* Check & modify the `main.tf` for the VMs 
* In `/infra` folder, (when terraform asks for confirmation, reply `yes`)
  * To setup infra, run `terraform apply`
  * To format the code, run `terraform fmt` to format the code after, any code changes
  * To validate changes, run `terraform validate` to validate any code changes
  * To destroy infra, run `terraform destroy`

## Resources

* Blueprints: https://cloud.google.com/docs/terraform/blueprints/terraform-blueprints
* Hashicorp: https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance