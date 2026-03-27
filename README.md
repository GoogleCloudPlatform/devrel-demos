# Google Cloud DevRel Demos

This repository contains code that supports talks, blogs, workshops, and other activities the Google Cloud Developer Relations team engages in. It serves as a central hub for practical examples and proof-of-concepts across various Google Cloud products and services.

## Repository Structure

The repository is organized by domain and technology area:

*   **[agents/](./agents)**: Autonomous AI agents and diagnostic tools (e.g., AIDA, Cymbal Transit).
*   **[ai-ml/](./ai-ml)**: Machine Learning demos, including Vertex AI, Gemini API, RAG techniques, and model fine-tuning.
*   **[app-dev/](./app-dev)**: Application development on Google Cloud, covering Cloud Run, Cloud Functions, and various frameworks.
*   **[codelabs/](./codelabs)**: Source code for interactive codelabs.
*   **[containers/](./containers)**: Containerization and orchestration demos for GKE and Cloud Run.
*   **[data-analytics/](./data-analytics)**: Data processing and analytics examples using BigQuery, Apache Beam, Kafka, and Dataproc.
*   **[devops/](./devops)**: Observability, CI/CD, and infrastructure management (e.g., OpenTelemetry, GitHub Actions).
*   **[infrastructure/](./infrastructure)**: Infrastructure-focused demos for AlloyDB, Load Balancing, and more.
*   **[languages/](./languages)**: Language-specific samples and libraries.
*   **[security/](./security)**: Security-focused demos and best practices.

## How to use these demos

You can clone the entire repository to explore all samples:

```bash
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
```

### Pulling a single demo (Shallow Copy)

If you only want to download a specific folder without cloning the entire repository, you can use [giget](https://github.com/unjs/giget). This is faster and more efficient for trying out a single demo.

Use the following command format:

```bash
npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/<DEMO_PATH> <LOCAL_DEMO_FOLDER>
```

#### Example

To pull the **AIDA** agent demo into a local folder named `my-aida-demo`:

```bash
npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/agents/aida my-aida-demo
```

## Contributing

Please see [CONTRIBUTING.md](./.github/CONTRIBUTING.md) for details on how to contribute to this project.

## License

All code in this repository is licensed under the Apache 2.0 License. See [LICENSE](./LICENSE) for more information.
