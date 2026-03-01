# Google Cloud Model Armor Examples

This folder contains a collection of code examples and tutorials demonstrating how to implement and use **Google Cloud Model Armor** within your Generative AI applications.

## About Google Cloud Model Armor

Google Cloud Model Armor is a managed security service designed to help protect Generative AI applications from risks such as prompt injection, sensitive data leakage, and toxic content. It sits between your users and your large language models (LLMs), filtering both inbound prompts and outbound model responses based on policies you define.

**Useful Resources:**

* [Model Armor Official Documentation](https://cloud.google.com/security-command-center/docs/model-armor-overview)
* [Model Armor Floor Settings](https://docs.cloud.google.com/model-armor/configure-floor-settings)
* [Model Armor API Reference](https://docs.cloud.google.com/model-armor/reference/rest?rep_location=global)

---

## 📂 Examples included in this directory

Explore the subfolders below to see how Model Armor can be integrated into different architectures and use cases.

| Example | Description | Key Concepts Covered |
| :--- | :--- | :--- |
| **[integration-setup-terraform](./integration-setup-terraform)** | Demonstrates how to configure Model Armor integration with Vertex AI and Google Cloud MCP servers using Terraform. | Terraform plan to configure floor settings and integration. |
| **[sanitiation-quickstart](./sanitization-quickstart)** | A beginner-friendly example showing how to call Model Armor sanitiation API using Python client library. | API Initialization, Basic Request/Response sanitization. |

---

## 🛠 Prerequisites

Before running any of the examples in these subfolders, ensure you have:

1. A Google Cloud Project with billing enabled.
2. The **Model Armor API** enabled in your project.
3. A valid Service Account with the `roles/modelarmor.admin` or `roles/modelarmor.user` IAM role.
4. Authenticated your local environment using the Google Cloud CLI:

   ```bash
   gcloud auth application-default login
   ```

Please refer to the `README.md` inside each specific subfolder for individual setup instructions and dependencies.
