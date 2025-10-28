# GenAI Chatbot with Advanced Model Armor Integration

This web application demonstrates a sophisticated integration of Google Cloud's Vertex AI foundation models with Model Armor. It provides a highly configurable and performant interface for testing prompt/response sanitization and multimodal interactions.

## Key Features

* **Text and File Input Types**: Supports file uploads (PDF, DOCX, PPTX, XLSX) in addition to text prompts, enabling analysis of document-based content.
* **Advanced Model Armor Analysis**:
    * Dynamically loads Model Armor templates based on the selected GCP region.
    * Provides a detailed breakdown of which Model Armor filters (Responsible AI, Sensitive Data, Jailbreak/PI, etc.) passed or failed for both the prompt and the model's response.
    * Option to view the raw JSON output from the Model Armor API for in-depth analysis.
* **Configurable Safeguards**:
    * **System Instructions**: Set a persistent system-level instruction to guide the model's behavior across a conversation.
    * **Default Responses**: Configure the application to return a pre-defined default response if either the prompt or the model's output violates a policy.
* **Performance Optimizations**:
    * **Asynchronous Processing**: The backend leverages `asyncio` to perform prompt analysis and model generation in parallel for a faster user experience.
    * **Backend Caching**: Caches Model Armor API results and templates to reduce latency and redundant API calls.
    * **Optimized HTTP Client**: Uses an HTTP session with connection pooling and automatic retries for more resilient communication with Google Cloud APIs.

## Prerequisites

1.  A Google Cloud Project with the following APIs enabled:
    * Vertex AI API (`aiplatform.googleapis.com`)
    * Model Armor API (`modelarmor.googleapis.com`)
2.  A service account with the necessary permissions to access Vertex AI and Model Armor.
3.  Model Armor templates created in your project. These templates must be in the same region as your DLP templates and be accessible to your service account.

## Setup

1.  **Clone the repository.**

2.  **Enable the necessary APIs:**
    ```bash
    gcloud services enable aiplatform.googleapis.com
    gcloud services enable modelarmor.googleapis.com
    ```

3.  **Create a `.env` file** and update it with your project details:
    ```
    GCP_PROJECT_ID=your-project-id
    GCP_LOCATION=your-region # e.g., us-central1
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the application locally:**
    ```bash
    python app.py
    ```

## Deployment to Cloud Run

This application is ready for containerization and deployment.

1.  **Build the container image using Cloud Build:**
    ```bash
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/model-armor-chat
    ```

2.  **Deploy to Cloud Run:**
    ```bash
    gcloud run deploy model-armor-chat \
      --image gcr.io/YOUR_PROJECT_ID/model-armor-chat \
      --platform managed \
      --region YOUR_REGION \
      --allow-unauthenticated \
      --set-env-vars="GCP_PROJECT_ID=YOUR_PROJECT_ID"
    ```
    *Note: For production, you should configure appropriate authentication and security settings.*
