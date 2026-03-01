# Google Cloud Model Armor Examples

This folder contains a collection of code examples and tutorials demonstrating how to implement and use **Google Cloud Model Armor** within your Generative AI applications.

## About Google Cloud Model Armor

Google Cloud Model Armor is a managed security service designed to help protect Generative AI applications from risks such as prompt injection, sensitive data leakage, and toxic content. It sits between your users and your large language models (LLMs), filtering both inbound prompts and outbound model responses based on policies you define.

**Useful Resources:**

* [Model Armor Official Documentation](https://cloud.google.com/security-command-center/docs/model-armor-overview)
* [Configure Model Armor Policies](https://cloud.google.com/security-command-center/docs/how-to-use-model-armor)
* [Model Armor API Reference](https://cloud.google.com/model-armor/docs/reference/rest)

---

## 📂 Examples included in this directory

Explore the subfolders below to see how Model Armor can be integrated into different architectures and use cases.

| Example | Description | Key Concepts Covered |
| :--- | :--- | :--- |
| **[01-basic-setup](./01-basic-setup)** | A beginner-friendly example showing how to initialize Model Armor and run a simple prompt evaluation. | API Initialization, Basic Request/Response filtering. |
| **[02-dlp-integration](./02-dlp-integration)** | Demonstrates how to configure Model Armor to work with Cloud Data Loss Prevention (DLP) to mask PII in model responses. | Cloud DLP integration, PII masking, Policy routing. |
| **[03-langchain-interceptor](./03-langchain-interceptor)** | Shows how to build a custom LangChain middleware that intercepts requests and routes them through Model Armor before hitting Vertex AI. | LangChain callbacks, Vertex AI, Custom middleware. |
| **[04-prompt-injection-defense](./04-prompt-injection-defense)** | A practical scenario showcasing how Model Armor detects and blocks malicious jailbreak attempts. | Jailbreak detection, Block lists, Error handling. |

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
