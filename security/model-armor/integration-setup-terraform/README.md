# Model Armor Integration with Vertex AI Sample

This folder contains a Terraform sample demonstrating how to configure the integration of Google Cloud Model Armor with **Vertex AI** and **Google Cloud MCP (Model Context Protocol) servers** for a given Google Cloud project.

The sample assumes that Model Armor floor settings in the project are already configured. See [configure floor settings](https://docs.cloud.google.com/model-armor/configure-floor-settings) for more details.

---

## 🔐 Required Permissions

The credentials used to execute the plan has to have the **Model Armor Admin** (`roles/modelarmor.admin`) role.

---

## 🛠️ Input Variables

This Terraform module relies on input variables to customize the deployment for your specific environment. You can provide these via a `terraform.tfvars` file or directly in the CLI.

| Variable Name | Description | Type | Required |
| :--- | :--- | :--- | :--- |
| `project_id` | The Google Cloud project ID where resources will be deployed. | `string` | **Yes** |
| `vertex_ai_integration` | Flag to configure Vertex AI integration. Default is `true`. | `bool` | No |
| `mcp_integration` | Flag to configure MCP servers integration. Default is `false`. | `bool` | No |

---

## 🚀 How to Run the Sample

Follow these steps to run the sample in the local environment:

1. **Authenticate via Google Cloud CLI** (if running locally):

    ```bash
    gcloud auth application-default login
    ```

2. **Initialize Terraform**:
    Downloads the necessary providers and initializes the backend.

    ```bash
    terraform init
    ```

3. **Review the Execution Plan**:
    Preview the resources Terraform will create or modify. You will be prompted to enter any missing variables.

    ```bash
    terraform plan
    ```

    *(Tip: You can create a `terraform.tfvars` file with your variables to skip the prompts).*

4. **Apply the Configuration**:
    Execute the plan to provision the integration.

    ```bash
    terraform apply
    ```

    Type `yes` when prompted to confirm the deployment.

---

## ✅ How to Check That It Worked

Once `terraform apply` completes successfully, you can verify the integration using the following methods:

* **Google Cloud Console**: Navigate to the **Model Armor** section in the Google Cloud Console. You should see your specified Vertex AI Endpoint and MCP Server listed under the "Protected Resources" or "Integrations" tab, bound to the correct template.
