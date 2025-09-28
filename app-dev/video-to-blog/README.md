# Video to Blog Post Generator

This application is a learning resource that demonstrates how to build a
full-stack, multi-agent, generative AI application using Python, Flask, and Google Cloud.

## Purpose

The application takes a YouTube video URL as input, uses Google's generative AI
models to create a blog post from the video's content, and generates a header
image for the post. It's a practical example of how to integrate and deploy
generative AI in a web application. The application also includes an optional AI
agent that allows for collaborative editing of the generated blog post.

## Two-Part Application

This project consists of two main components:

1.  **The Web App:** A Flask-based web application that generates a blog post from a YouTube video. You can run this part by itself.
2.  **The ADK App (Optional):** An agent built with the Agent Development Kit (ADK) that allows for collaborative, agentic editing of the generated blog post. If you want to use the editing feature, you'll need to run this app as well.

## Project Structure

```
.
├── app.py                  # Main Flask application
├── Dockerfile              # Instructions for building the container image
├── prompts.py              # Prompts for the generative AI models
├── requirements.txt        # Python dependencies for the web app
├── static
│   └── style.css           # Shared stylesheet for all pages
├── templates
│   ├── blog-post.html      # Template for the generated blog post page
│   └── index.html          # The main page of the application
└── blog_refiner/           # The optional ADK application for editing
    ├── blog_refiner/
    ├── pyproject.toml
    └── README.md
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
*   **ADK:** Google's Agent Development Kit, used to help the user edit the
    blog post.

## Prerequisites

Before you begin, you will need:

*   Python 3.11 or later
*   `pip` for installing Python packages
*   [Poetry](https://python-poetry.org/docs/) for the ADK app's dependency management
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

---

## How to Run the Application

You have three main options for running the application: running just the web app for blog generation, running both the web app and the ADK app to include the editing feature, or running only the ADK app to experiment with the editing agents.

### Option 1: Run Only the Web App Locally

Follow these steps if you only want to generate blog posts without the agentic editing feature. Make sure you are in the `video-to-blog` directory (the project root) before running the commands below.

1.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(Note: On Windows, the activate command is `venv\Scripts\activate`)*

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure your Project ID:**
    Create a file named `.env` in the `video-to-blog` directory and add your
    Google Cloud Project ID to it:
    ```
    PROJECT_ID=your-gcp-project-id
    ```

4.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:8080`.

### Option 2: Run Both the Web App and the ADK App Locally

Follow these steps to use the agentic editing feature locally. You will need two separate terminal windows: one for the ADK app and one for the web app.

1.  **Set up and run the ADK app (in Terminal 1):**

    a. **Navigate to the `blog_refiner` directory:**
    ```bash
    cd blog_refiner
    ```

    b. **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(Note: On Windows, the activate command is `venv\Scripts\activate`)*

    c. **Install Poetry and dependencies:**
    ```bash
    pip install poetry
    poetry install
    ```

    d. **Configure Google Cloud credentials for the ADK app:**
    Create a `.env` file inside the `blog_refiner` directory with the following content:
    ```
    GOOGLE_GENAI_USE_VERTEXAI=true
    GOOGLE_CLOUD_PROJECT=<your-project-id>
    GOOGLE_CLOUD_LOCATION=<your-project-location>
    ```

    e. **Authenticate with gcloud:**
    ```bash
    gcloud auth application-default login
    gcloud auth application-default set-quota-project <your-project-id>
    ```

    f. **Run the ADK API server:**
    ```bash
    adk api_server --port=8000 .
    ```
    This will start a local API server for the agent at `http://127.0.0.1:8000`. Keep this terminal running.

2.  **Set up and run the Web App (in Terminal 2):**

    a. **Navigate to the `video-to-blog` directory.**

    b. **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(Note: On Windows, the activate command is `venv\Scripts\activate`)*

    c. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

    d. **Configure the `.env` file:**
    Create or edit the `.env` file in the `video-to-blog` directory. It should contain your Project ID and the URL of the running ADK agent:
    ```
    PROJECT_ID=<your-project-id>
    AGENT_URL=http://127.0.0.1:8000
    ```

    e. **Run the application:**
    ```bash
    python app.py
    ```
    The main application will be available at `http://127.0.0.1:8080`. You can now generate a blog post and use the textbox at the bottom to interact with the editing agent.

### Option 3: Run Only the ADK App for Blog Refining

Follow these steps if you just want to try the agents that help with refining a blog post.

1.  **Navigate to the `blog_refiner` directory:**
    ```bash
    cd blog_refiner
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(Note: On Windows, the activate command is `venv\Scripts\activate`)*

3.  **Install Poetry and dependencies:**
    ```bash
    pip install poetry
    poetry install
    ```

4.  **Configure Google Cloud credentials for the ADK app:**
    Create a `.env` file inside the `blog_refiner` directory with the following content:
    ```
    GOOGLE_GENAI_USE_VERTEXAI=true
    GOOGLE_CLOUD_PROJECT=<your-project-id>
    GOOGLE_CLOUD_LOCATION=<your-project-location>
    ```

5.  **Authenticate with gcloud:**
    ```bash
    gcloud auth application-default login
    gcloud auth application-default set-quota-project <your-project-id>
    ```

6.  **Run the ADK web interface:**
    ```bash
    adk web
    ```
    This will start a web server and print the URL. Open the URL in your browser. In the web UI, paste in a blog post, and then you can ask the AI to tweak the blog post (for example, by making it more conversational), or you can ask the AI to give you suggestions for improvements.

---

## How to Deploy to Cloud Run

You can deploy one or both parts of the application to Cloud Run. If you want to use the agentic editing feature, you must deploy the ADK app first to get its service URL.

### Step 1: Deploy the ADK App to Cloud Run (Optional)

1.  **Navigate to the `blog_refiner` directory:**
    ```bash
    cd blog_refiner
    ```

2.  **Run the deployment command:**
    Replace `[YOUR_PROJECT_ID]` and `[REGION]` with your values.
    ```bash
    GOOGLE_CLOUD_PROJECT="[YOUR_PROJECT_ID]"
    GOOGLE_CLOUD_LOCATION="[REGION]"
    SERVICE_NAME="blog-refiner"
    AGENT_PATH="./blog_refiner"

    adk deploy cloud_run \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$GOOGLE_CLOUD_LOCATION \
        --service_name=$SERVICE_NAME \
        $AGENT_PATH
    ```

3.  **Copy the Service URL:**
    The deployment will end with a message like this:
    ```
    Done.
    Service [blog-refiner] revision [blog-refiner-00001-abc] has been deployed and is serving 100 percent of traffic.
    Service URL: https://blog-refiner-xxxxxxxxxx-uc.a.run.app
    ```
    **Copy this `Service URL`.** You will need it for the web app's configuration.

### Step 2: Deploy the Web App to Cloud Run

1.  **Navigate to the `video-to-blog` directory.**

2.  **Create or update the `.env` file:**
    Add your Project ID and, if you deployed the ADK app, the `Service URL` you copied.

    *If you deployed the ADK app:*
    ```
    PROJECT_ID=[YOUR_PROJECT_ID]
    AGENT_URL=[SERVICE_URL_FROM_STEP_1]
    ```

    *If you are NOT using the ADK app:*
    ```
    PROJECT_ID=[YOUR_PROJECT_ID]
    ```

3.  **Run the deployment command:**
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
*   `blog_refiner/blog_refiner/root_agent.py`: The main "coordinator" agent that receives the user's request and delegates tasks to the other agents.
*   `blog_refiner/blog_refiner/updater_agent.py`: This agent takes the blog post and the user's instructions and generates an updated version of the blog post.
*   `blog_refiner/blog_refiner/critic_agent.py`: This agent critiques the blog post and provides suggestions for improvement.
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

```