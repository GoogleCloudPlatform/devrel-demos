### Nano Banana Pro MCP Server Deployment

To deploy and run the Nano Banana Pro MCP server to [Cloud Run](https://docs.cloud.google.com/run/docs), follow these steps:

1.  **Configure Environment Variables:**
    Copy the provided `.env-template` file to `.env`:
    ```bash
    cp .env-template .env
    ```
    Then, open `.env` and edit the necessary variables, such as project ID, Cloud Storage Bucket, or any other configuration specific to your environment.

2.  **Deploy the Server:**
    Execute the deployment script:
    ```bash
    ./deploy.sh
    ```
    This script will handle the build and deployment process for the MCP server.
