> [!NOTE] 
> This sample has been added to the official Google Cloud Python docs samples repository.
>
> It can be found at [GoogleCloudPlaform/python-docs-samples/run/mcp-server](https://github.com/GoogleCloudPlatform/python-docs-samples/tree/main/run/mcp-server).
>
> For a step-by-step walkthrough read ["Build and Deploy a remote MCP Sever to Google Cloud Run"](https://cloud.google.com/blog/topics/developers-practitioners/build-and-deploy-a-remote-mcp-server-to-google-cloud-run-in-under-10-minutes/?e=48754805) Google Cloud blog post.
 
# Build and Deploy a remote MCP server to Cloud Run in 10 minutes ☁️ 🚀 

## 🔢 Math MCP Server Example

We will use [FastMCP](https://gofastmcp.com/getting-started/welcome) to create
a simple math MCP server that has two tools: `add` and `subtract`. FastMCP
provides a fast, Pythonic way to build MCP servers and clients.


### Transport

We will use the `streamable-http` transport for this example as it is the
recommended transport for remote servers as of the [2025-03-26 spec](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http),
but you can also still use `sse` if you prefer as it is backwards compatible.

If you want to use `sse` you will need to update the last line of
`server.py` to use `transport="sse"`.

## Prerequisites

- Python 3.10+ (FastMCP requires 3.10+)
- Google Cloud SDK (gcloud)
- Git (for cloning the repository)

## Installation

Set your Google Cloud credentials and project.

```bash
gcloud auth login
export PROJECT_ID=<your-project-id>
gcloud config set project $PROJECT_ID
```

## Deploying to Cloud Run

Now let's deploy a simple MCP server to Cloud Run. You can deploy directly from source or using a container image.

For both options we will use the `--no-allow-unauthenticated` flag to require authentication.

This is important for security reasons. If you don't require authentication, anyone can call your MCP server and potentially cause damage to your system.

<details open>
<summary>Deploy from source</summary>

```bash
gcloud run deploy mcp-server --no-allow-unauthenticated --region=us-central1 --source .
```

</details>

<details>
<summary>Deploy from a container image</summary>

Create an Artifact Registry repository to store the container image.

```bash
gcloud artifacts repositories create remote-mcp-servers \
  --repository-format=docker \
  --location=us-central1 \
  --description="Repository for remote MCP servers" \
  --project=$PROJECT_ID
```

Build the container image and push it to Artifact Registry with Cloud Build.

```bash
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$PROJECT_ID/remote-mcp-servers/mcp-server:latest
```

Deploy the container image to Cloud Run.

```bash
gcloud run deploy mcp-server \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/remote-mcp-servers/mcp-server:latest \
  --region=us-central1 \
  --no-allow-unauthenticated
```

</details>

If your service has successfully deployed you will see a message like the following:

```bash
Service [mcp-server] revision [mcp-server-12345-abc] has been deployed and is serving 100 percent of traffic.
```

## Authenticating MCP Clients

Since we specified `--no-allow-unauthenticated` to require authentication, any
MCP client connecting to our remote MCP server will need to authenticate.

The official docs for [Host MCP servers on Cloud Run](https://cloud.google.com/run/docs/host-mcp-servers#authenticate_mcp_clients)
provides more information on this topic depending on where you are running your MCP client.

For this example we will run the [Cloud Run proxy](https://cloud.google.com/sdk/gcloud/reference/run/services/proxy)
to create an authenticated tunnel to our remote MCP server on our local machines.

By default, the URL of Cloud Run services requires all requests to be
authorized with the [Cloud Run Invoker](https://cloud.google.com/run/docs/securing/managing-access#invoker)
(`roles/run.invoker`) IAM role. This IAM policy binding ensures that a
strong security mechanism is used to authenticate your local MCP client.

You should make sure that you or any team members trying to access the remote
MCP server have the `roles/run.invoker` IAM role bound to their Google Cloud
account.


> [!TIP] 
> The below command may prompt you to download the Cloud Run proxy if it is
> not already installed. Follow the prompts to download and install it.

```bash
gcloud run services proxy mcp-server --region=us-central1
```

You should see the following output:

```bash
Proxying to Cloud Run service [mcp-server] in project [<YOUR_PROJECT_ID>] region [us-central1]
http://127.0.0.1:8080 proxies to https://mcp-server-abcdefgh-uc.a.run.app
```

All traffic to `http://127.0.0.1:8080` will now be authenticated and forwarded to
our remote MCP server.

## Testing our remote MCP server

Let's test and connect to our remote MCP server using the
[test_server.py](test_server.py) test script. It uses the FastMCP client to
connect to `http://127.0.0.1:8080/mcp` (note the `/mcp` at the end as we
are using the `streamable-http` transport) and call the `add` and `subtract` tools.

> [!NOTE]
> Make sure you have the Cloud Run proxy running before running the test server.

In a **new terminal** run:

```bash
uv run test_server.py
```

You should see the following output:

```bash
>>> 🛠️  Tool found: add
>>> 🛠️  Tool found: subtract
>>> 🪛  Calling add tool for 1 + 2
<<< ✅ Result: 3
>>> 🪛  Calling subtract tool for 10 - 3
<<< ✅ Result: 7
```

You have done it! You have successfully deployed a remote MCP server to Cloud
Run and tested it using the FastMCP client.
