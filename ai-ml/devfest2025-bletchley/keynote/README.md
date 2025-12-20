# Go for GenAI!

This is the companion repository for the keynote at **DevFest Bletchley Park 2025** entitled "Go for GenAI!".


**Slides:** [Go for GenAI](https://speakerdeck.com/danicat/go-for-genai)

## Contents

### [01. Genkit Demo](./01-genkit-demo/)
A structured workflow built with **Genkit**. It demonstrates how to define and run linear flows for generative AI tasks.
-   **Features:** Simple prompt execution, model selection.
-   **Backend:** Vertex AI (Gemini).

### [02. Genkit Server Demo](./02-genkit-server-demo/)
A simple flow server built with **Genkit**. It demonstrates how to run a flow as a server for UI interaction.
-   **Features:** Flow server, Dev UI support.
-   **Backend:** Vertex AI (Gemini).

### [03. ADK Demo](./03-adk-demo/)
A conversational agent built with the **Agent Development Kit (ADK)**. It demonstrates how to build stateful, interactive agents that can run in the console or as a web service.
-   **Features:** Interactive chat, model selection, multiple launcher modes (console/web).
-   **Backend:** Vertex AI (Gemini).

## Getting Started

1.  **Prerequisites:**
    -   Go 1.24+
    -   Google Cloud Project with Vertex AI enabled.
    -   `gcloud` CLI authenticated.
    -   [Genkit CLI](https://firebase.google.com/docs/genkit/get-started) (optional, for UI interaction with Genkit demos).
        ```bash
        curl -sL cli.genkit.dev | bash
        ```

2.  **Setup:**
    Set your project ID:
    ```bash
    export GOOGLE_CLOUD_PROJECT="your-project-id"
    ```
    Alternatively, you can create a `.env` file in the project root with the following content:
    ```env
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=us-central1
    GOOGLE_GENAI_USE_VERTEXAI=1
    ```

3.  **Run:**
    Navigate to the specific demo directory and follow the instructions in its `README.md`.

    ```bash
    cd 01-genkit-demo
    # or
    cd 02-genkit-server-demo
    # or
    cd 03-adk-demo
    ```