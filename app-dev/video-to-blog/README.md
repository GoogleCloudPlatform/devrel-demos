# Video to Blog Post Generator

This application is a learning resource that demonstrates how to build a
full-stack, generative AI application using Python, Flask, and Google Cloud.

## Purpose

The application takes a YouTube video URL as input, uses Google's generative AI
models to create a blog post from the video's content, and generates a header
image for the post. It's a practical example of how to integrate and deploy
generative AI in a web application.

## Project Structure

```
.
├── app.py                  # Main Flask application
├── Dockerfile              # Instructions for building the container image
├── prompts.py              # Prompts for the generative AI models
├── requirements.txt        # Python dependencies
├── static
│   └── style.css           # Shared stylesheet for all pages
├── templates
│   ├── blog-post.html      # Template for the generated blog post page
│   └── index.html          # The main page of the application
└── util.py                 # Utility functions
```

## Key Concepts

*   **Flask:** A lightweight web framework for Python used to build the web
    application and API.
*   **Docker:** A platform for containerizing the application, ensuring it runs
    consistently in any environment.
*   **Cloud Run:** A fully managed serverless platform on Google Cloud for
    deploying and scaling containerized applications.
*   **Gemini:** Google's family of generative AI models, used here to generate
    the blog post text from the video.
*   **Imagen:** Google's text-to-image model, used to generate the header image
    for the blog post.

## Prerequisites

Before you begin, you will need:

*   Python 3.10 or later
*   `pip` for installing Python packages
*   A Google Cloud project
*   The Google Cloud SDK (`gcloud` CLI) installed and configured

## APIs to Enable

To run this application, you'll need to enable the following APIs in your
Google Cloud project. You can do this by running the following command:

```bash
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com
```

*   **Cloud Build API:** (`cloudbuild.googleapis.com`)
*   **Cloud Run Admin API:** (`run.googleapis.com`)
*   **Vertex AI API:** (`aiplatform.googleapis.com`)
*   **Artifact Registry API:** (`artifactregistry.googleapis.com`)

## How to Run Locally

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure your Project ID:**
    Create a file named `.env` in the root of the project and add your
    Google Cloud Project ID to it:
    ```
    PROJECT_ID=your-gcp-project-id
    ```

3.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:8080`.

## How to Deploy to Cloud Run

This application is configured for a source-based deployment to Cloud Run.

1.  **Make sure you are in the root directory of the project.**

2.  **Run the deployment command:**
    Replace `[SERVICE-NAME]` and `[REGION]` with your desired values (e.g.,
    `video-to-blog` and `us-central1`).
    ```bash
    gcloud run deploy [SERVICE-NAME] --source . --platform managed \
        --region [REGION] --allow-unauthenticated
    ```
    This command will automatically build the container image and deploy it to
    Cloud Run.

## Code Overview

*   `app.py`: This is the core of the application. It contains the Flask
    routes, the logic for handling form submissions, and the calls to the
    generative AI models.
*   `util.py`: Contains utility functions, such as `get_project_id()`, which
    cleverly determines the Google Cloud project ID.
*   `prompts.py`: This file stores the prompts that are sent to the Gemini and
    Imagen models. Separating them here makes them easy to edit and manage.
*   `requirements.txt`: Lists all the Python libraries that the application
    depends on.
*   `Dockerfile`: Defines the steps to build the container image for the
    application. It specifies the base image, copies the code, installs
    dependencies, and sets the command to run the application with Gunicorn.
*   `templates/index.html`: The HTML for the main page where users submit the
    YouTube link.
*   `templates/blog-post.html`: The HTML for the page that displays the
    generated blog post and header image.
*   `static/style.css`: The shared stylesheet for both HTML pages.
