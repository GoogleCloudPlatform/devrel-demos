# Podcast Assistant

This project is a podcast assistant that automates various tasks related to podcast publishing using generative AI. It can transcribe audio files, generate show notes, create blog posts, and draft social media posts. All of the generated materials should be reviewed and edited by a human before being used in publishing. This example is based on the [How to deploy a secure MCP server on Cloud Run Codelab](https://codelabs.developers.google.com/codelabs/cloud-run/how-to-deploy-a-secure-mcp-server-on-cloud-run#0).

## Features

- **Audio Transcription:** Transcribes audio files (`.mp3`, `.wav`) into text.
- **Show Notes Generation:** Creates a markdown-formatted list of topics and resources mentioned in the podcast.
- **Blog Post Generation:** Generates a detailed blog post summarizing the key topics and takeaways from the podcast.
- **Social Media Post Generation:** Drafts social media posts for X (formerly Twitter) and LinkedIn.

## About MCP Servers

A Multi-tool Control Plane (MCP) server is a backend service that exposes a set of tools that a language model can call to interact with an external environment. This project is an example of an MCP server that provides tools for podcast production. By deploying this server, you can learn how to create and manage your own MCP servers, which can be used to extend the capabilities of generative AI models.

## Getting Started

### Prerequisites

- Google Cloud SDK
- A Google Cloud project with the Vertex AI API enabled.
- A Google Cloud Storage bucket.
- Gemini CLI (for using/testing the MCP server)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
    cd devrel-demos/containers/podcast-assistant-mcp
    ```

2.  **Set up environment variables:**
    Copy the `.env.example` file to `.env` and fill in the required values.
    ```bash
    cp .env.example .env
    ```
    **Then, open the `.env` file and add your specific configuration details for `GCP_PROJECT_ID` and `GCS_BUCKET_NAME`.**

### Deploying to Cloud Run

1.  **Enable the Artifact Registry, Cloud Build, and Cloud Run APIs:**
    ```bash
    gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com storage.googleapis.com
    ```

2.  **Build and deploy the container image:**
    ```bash
    gcloud run deploy podcast-assistant --no-allow-unauthenticated --source . --region us-central1 --set-env-vars="GCP_PROJECT_ID=your-gcp-project-id,GCS_BUCKET_NAME=your-gcs-bucket-name"
    ```

    By using the --no-allow-unauthenticated command, we ensure that only authenticated Google Cloud users can use this MCP server.

## Using this MCP server
A convenient way to make use of this MCP server is by using it with Gemini CLI. Because this MCP server will only allow authenticated connections, we need to ensure a user connecting with the MCP server via Gemini CLI is authenticated. This section lists a couple of ways to do this.

If you wanted to use this MCP server with another program, like using it through an agent, you would want to make sure that program or agent is authenticating with the MCP server via a service account. This Readme does not include instructions for this use case.

There are three options for authenticating with the MCP server:
- **Option 1: Using an authentication token with Gemini CLI:** This method is quick to set up and is useful for temporary access to the MCP server. The token is valid for one hour.
- **Option 2: Using a proxy with Gemini CLI:** This method is more robust and is recommended for continuous development. The proxy automatically handles authentication and forwards requests to the MCP server.
- **[Example] Option 3: Using a service account** Options 1 & 2 involve authenticating as a user via Gemini CLI. This method involves authenticating as a service or agent (rather than a user) via a service account. This project does not include such a service or agent, so this option is provided as an example for reference, and is not immediately usable just from deploying this project.

### Option 1: Using an authentication token with Gemini CLI

This method uses an identity token associated with your Google Cloud account to authenticate with the MCP server. The ID token is good for one hour, so a user would need to get a new ID token if they want to use the MCP server again after one hour.

1. Give your user account permission to call the remote MCP server

    ```bash
    gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT --member=user:$(gcloud config get-value account) --role='roles/run.invoker'
    ```

2. Save your Google Cloud credentials and project number in environment variables for use in the Gemini Settings file:

    ```bash
    export PROJECT_NUMBER=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT --format="value(projectNumber)")
    export ID_TOKEN=$(gcloud auth print-identity-token)
    ```
    The second export command above creates and stores the ID token. A user would need to run this command again to use the MCP server more than one hour after this ID token was created.

3. Configure Gemini CLI
    Make a .gemini folder if it has not already been created
    mkdir -p ~/.gemini

    Update your .gemini/settings.json file to connect to the podcast-assistant MCP server via the local proxy. Note that the below command rewrites your Gemini CLI settings.json file, so any previously configured MCP servers or settings will be removed. To avoid this, edit the settings.json file directly and just add the "podcast-asssistant" block within your mcpServers block (or add the whole mcpServers block if you don't have one).

    ```bash
    echo "{
        \"ide\": {
            \"hasSeenNudge\": true
        },
        \"mcpServers\": {
            \"podcast-assistant\": {
                \"httpUrl\": \"https://podcast-assistant-$PROJECT_NUMBER.us-central1.run.app/mcp\",
                \"headers\": {
                    \"Authorization\": \"Bearer $ID_TOKEN\"
                }
            }
        }
    }" > ~/.gemini/settings.json
    ```

Now when you run Gemini CLI, the server should be connected, and you should be authenticated to use the MCP server as your Google Cloud user.

Run Gemini CLI by running:
```bash
gemini
```

Then give Gemini CLI the /mcp command to check that the MCP server is connected.

### Option 2: Using a proxy with Gemini CLI
For a more long-lasting connection between Gemini CLI and the MCP Server, consider connecting to the Cloud Run service by running a proxy.

1. Grant the "Cloud Run Invoker" Role

  First, you need to give your user account permission to invoke your Cloud Run service.
  ```bash
  gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT --member=user:$(gcloud config get-value account) --role='roles/run.invoker'
  ```

  Replace your-email@example.com with the email address you use for gcloud.

  2. Start the Proxy

  Now, start the gcloud run proxy in a separate terminal. It will run in the foreground and print connection information.

  ```bash
  gcloud run services proxy podcast-assistant --region=us-central1 --port=8080
  ```

  This command will forward requests from http://localhost:8080 on your local machine to your deployed Cloud Run service, automatically adding the necessary authentication headers.

  3. Configure the Gemini CLI
  Make a .gemini folder if it has not already been created
  ```bash
  mkdir -p ~/.gemini
  ```

  Update your .gemini/settings.json file to connect to the podcast-assistant MCP server via the local proxy. Note that the below command rewrites your Gemini CLI settings.json file, so any previously configured MCP servers or settings will be removed. To avoid this, edit the settings.json file directly and just add the "podcast-asssistant" block within your mcpServers block (or add the whole mcpServers block if you don't have one).

  ```bash
  echo "{
      "ide": {
          "hasSeenNudge": true
      },
      "mcpServers": {
          "podcast-assistant": {
              "httpUrl": "http://localhost:8080/mcp"
          }
      },
  }" > ~/.gemini/settings.json
  ```

  Now, when you use the gemini command, it will send requests to the local proxy, which will then securely forward them to your Cloud Run service. You can now use the --no-allow-unauthenticated flag on your Cloud Run service, and your Gemini CLI will be able to securely connect to it.

### [Example] Option 3: Using a service account

For services or agents that need to interact with the MCP server, you can use a service account to authenticate. This project does not include a service or agent. This section is provided as an example.

1.  **Create a service account:**

    ```bash
    gcloud iam service-accounts create podcast-assistant-agent --display-name="Podcast Assistant Agent"
    ```

2.  **Grant the service account the "Run Invoker" role:**

    ```bash
    gcloud run services add-iam-policy-binding podcast-assistant --member="serviceAccount:podcast-assistant-agent@${GCP_PROJECT_ID}.iam.gserviceaccount.com" --role="roles/run.invoker" --region=us-central1
    ```

3.  **Authenticate as the service account and call the MCP server:**

    An agent or service can use the service account's credentials to generate an OIDC token and include it in the `Authorization` header of its requests. The following `curl` command demonstrates this process:

    ```bash
    # Get the URL of the Cloud Run service
    SERVICE_URL=$(gcloud run services describe podcast-assistant --platform managed --region us-central1 --format 'value(status.url)')

    # Get an OIDC token from the service account
    AUTH_TOKEN=$(gcloud auth print-identity-token --impersonate-service-account="podcast-assistant-agent@${GCP_PROJECT_ID}.iam.gserviceaccount.com")

    # Call the MCP server to list the available tools
    curl -X POST -H "Authorization: Bearer ${AUTH_TOKEN}" -H "Content-Type: application/json" -d '{"tool_code": "print(default_api.list_tools())"}' ${SERVICE_URL}/mcp
    ```

### Available Tools

The application exposes the following tools:

- `generate_transcript(audio_file_uri, episode_name)`: Generates a transcript from an audio file.
  - `audio_file_uri`: The GCS URI of the audio file (e.g., `gs://your-bucket/your-audio.mp3`).
- `generate_shownotes(transcript_gcs_uri, episode_name)`: Generates show notes from a transcript.
  - `transcript_gcs_uri`: The GCS URI of the transcript file (e.g., `gs://your-bucket/transcripts/your-episode.json`).
- `generate_blog_post(transcript_gcs_uri, episode_name)`: Generates a blog post from a transcript.
  - `transcript_gcs_uri`: The GCS URI of the transcript file (e.g., `gs://your-bucket/transcripts/your-episode.json`).
- `generate_social_media_posts(transcript_gcs_uri, episode_name)`: Generates social media posts from a transcript.
  - `transcript_gcs_uri`: The GCS URI of the transcript file (e.g., `gs://your-bucket/transcripts/your-episode.json`).
