# 🎻 Music Education Multi-Agent with ADK and A2A 🎼

This sample demonstrates how [Agent2Agent](https://a2a-protocol.org/) protocol helps AI agents collaborate with each other.

The [Agent2Agent (A2A)](https://a2a-protocol.org/) Protocol is an open standard developed by Google and donated to the Linux Foundation designed to enable seamless communication and collaboration between AI agents.

## Introduction

There are 2 agents in this sample:

- Music Education Agent that helps students learn about classical compositions.
- Music History Agent that helps students learn about historical topics.

Both agents are built with [Agent Development Kit (ADK)](https://google.github.io/adk-docs/), but the Music History agent is available as an A2A agent,
that any other agent can call. And that's what Music Education Agent does using ADK's `RemoteA2aAgent` class.

![ADK Diagram](images/adk_diagram.png)

## Deploying production-ready A2A Agents

This sample demonstrates how to run and interact with A2A agents deployed to [Cloud Run](https://cloud.google.com/run).

### Handling Agent URL in A2A Agent Card

Music History Agent uses ADK's [`to_a2a` helper](https://google.github.io/adk-docs/a2a/quickstart-exposing/#exposing-the-remote-agent-with-the-to_a2aroot_agent-function) for exposing an ADK agent via A2A protocol.
It also adds an additional [middleware component](history_agent/a2a_utils.py) that handles rewriting of the agent's URL.

According to the [A2A specification](https://a2a-protocol.org/v0.3.0/specification/#55-agentcard-object-structure),
Agent's URL is the preferred endpoint URL for interacting with the agent.
Rewriting the agent's URL is necessary when the deployed agent can be accessed via different endpoint locations (protocol, hostname, port),
or when the URL is not known. For example, an agent deployed to Cloud Run may be accessible via multiple URLs:

- Standard Cloud Run URL (`https://[TAG---]SERVICE_NAME-PROJECT_NUMBER.REGION.run.app`)
- Custom domain with [Application Load Balancer](https://docs.cloud.google.com/run/docs/mapping-custom-domains#https-load-balancer) (e.g. `https://my-agent.example.com`)
- Reverse proxies, Cloud DNS, custom load balancers, etc.

With those services involved, the agent's container often doesn't have information about the actual URL the agent is accessed with.

ADK's A2A implementation, similarly to the majority of A2A servers, has the Agent Card co-located with the agent.
It allows rewriting the agent's URL in the card using the request information of the card's request.
To construct the agent URL, the rewriting component replaces scheme (protocol), hostname and port with the following information:

- Host - with `X-Forwarded-Host` value, if present, otherwise with the hostname of the AgentCard request.
- Port - with `X-Forwarded-Port` value, if present, otherwise with the port of the AgentCard request.
- Scheme - with `X-Forwarded-Proto` value, if present, otherwise with the scheme of the AgentCard request or `http`.

### Authentication for agents deployed to Cloud Run

All Cloud Run services are deployed privately by default,
which means that they can't be accessed without providing authentication credentials in the request.
These services are secured by Identity and Access Management.

When an agents makes a request to an A2A agent deployed in Cloud Run, they must perform [service-to-service authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).

Music Education Agent uses a an authentication extension for Httpx Client, implemented in [music_ed_agent/auth_utils.py](music_ed_agent/auth_utils.py).
It creates a custom `AsyncClient` when is passed to the ADK's `RemoteA2aAgent` constructor.

The extension handles service-to-service authentication, whether the calling agent is running locally or in Cloud.

## Run Locally

**Prerequisites**:

- Python 3.12
- A Google Cloud project.
- [uv](https://docs.astral.sh/uv/) (Python package manager)

**Install Dependencies**:

```bash
uv sync
```

**Configure the environment**:

These agents use [Vertex AI](https://cloud.google.com/vertex-ai) to access Gemini models in Google Cloud.

1. Rename `.env-sample` file to `.env`.
2. Set `GOOGLE_CLOUD_PROJECT` environment variable to the Id of your Google Cloud Project.
3. Set `GOOGLE_CLOUD_LOCATION` to the region to use with Vertex AI.
4. Enable Vertex AI APIs:

  ```bash
  source .env
  gcloud services enable run.googleapis.com aiplatform.googleapis.com --project ${GOOGLE_CLOUD_PROJECT}
  ```

**Run the Historical Context Agent (`RemoteA2AAgent`)**

Rather than running this in the ADK Web UI or with an interactive runner, we'll run this helper agent as a backend *API server* that our root Music Education Agent can call.

```bash
source .env
uv run uvicorn history_agent.agent:a2a_app --host localhost --port 8001
```

**Verify that the Agent Card is available over localhost**:

Navigate to: http://localhost:8001/.well-known/agent-card.json

*Expected output*:

```json
{"capabilities":{},"defaultInputModes":["text/plain"],"defaultOutputModes":["text/plain"],"description":"Agent that performs historical research using Wikipedia and Google Search","name":"historical_context_agent","preferredTransport":"JSONRPC","protocolVersion":"0.3.0","skills":[{"description":"Agent that performs historical research using Wikipedia and Google Search \nI am a history education agent that helps students learn about historical topics.\n\nI will be given a topic as a text query. my task is to search relevant knowledge bases for key, authoritative information about that topic.\n\nFor instance, if the topic is a person, look up biographical details about that person's life. If the topic is a historical event, research when and what happened.\n\nAlways try to contextualize my response - for instance, what were the broader historical events, movements, or figures that may have influenced this topic? How did this topic or event impact history?\n\nAVAILABLE TOOLS (KNOWLEDGE BASES):\n- Google Search (google_search_tool)\n- Wikipedia (adk_wikipedia_tool)\n\nDon't provide too much information back to the user, just key info broken into bullet points. Use emojis to make my response more readable.\n","id":"historical_context_agent","name":"model","tags":["llm"]},{"description":"A wrapper around Wikipedia. Useful for when you need to answer general questions about people, places, companies, facts, historical events, or other subjects. Input should be a search query.","id":"historical_context_agent-wikipedia","name":"wikipedia","tags":["llm","tools"]},{"description":"","id":"historical_context_agent-search_agent","name":"search_agent","tags":["llm","tools"]}],"supportsAuthenticatedExtendedCard":false,"url":"http://localhost:8001","version":"0.0.1"}
```

**[Optional] Run the A2A Inspector**:

```bash
git clone https://github.com/a2aproject/a2a-inspector.git
cd a2a-inspector
uv sync
cd frontend
npm install
cd ..
chmod +x run.sh
./run.sh
```

*Expected output*:

```bash
Starting backend server...
A2A Inspector is running!
Frontend PID: 36525
Backend PID: 36549
Press Ctrl+C to stop both services
[BACKEND] INFO:     Will watch for changes in these directories: ['/Users/username/a2a-inspector/backend']
[BACKEND] INFO:     Uvicorn running on http://127.0.0.1:5001 (Press CTRL+C to quit)
```

Open http://127.0.0.1:5001 in a browser. Then, enter the following as the Agent Card URL: `http://localhost:8001/.well-known/agent-card.json`

You should be able to see the agent card.

**Run the Music Education Agent**:

In another terminal tab, from the `music-education-a2a` root directory:

```bash
source .env
export REMOTE_AGENT_CARD="http://localhost:8001/.well-known/agent-card.json"
uv run adk web
```

> `REMOTE_AGENT_CARD` environment variable tells the Music Education Agent where to fetch the History Agent card from.

Open http://127.0.0.1:8000/dev-ui/?app=music_ed_agent in a browser.

**Test prompts:**
- Dvorak 9th Symphony 2nd movement
- Rachmaninov 2nd piano concerto 1st movement
- Brahms 3rd Symphony 3rd movement
- Bach - Goldberg Variations
- Mozart Sinfonia Concertante in E flat
- Mahler Symphony no. 2 finale
- Wagner Tristan und Isolde
- Sibelius Symphony no. 2
- Symphony No. 5 in C Minor, Op. 67 by Ludwig van Beethoven
- "Eine kleine Nachtmusik" (Serenade No. 13 for strings in G major), K. 525 by Wolfgang Amadeus Mozart:
- Toccata and Fugue in D Minor, BWV 565 by Johann Sebastian Bach:
-"Clair de lune" from Suite bergamasque by Claude Debussy
- "Ride of the Valkyries" from Die Walküre by Richard Wagner

... Or any classical music piece you want to learn more about!

**The agent will ask if you'd like to hear about the historical context if the chosen piece**,
and if you agree, it will call the Music History Agent for that.

Alternatively, you can ask it straight about the history of the piece (e.g. "History of Wagner Tristan und Isolde").

![ADK Web](images/adk_web_screenshot.png)

## Run in Google Cloud

**Prerequisites**:

- A Google Cloud project.
- gcloud CLI installed on your machine.

**Build and deploy history agent to Cloud Run** --

```bash
source .env
gcloud run deploy history-agent \
  --source history_agent \
  --region "${GOOGLE_CLOUD_LOCATION}" \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_GENAI_USE_VERTEXAI=true \
  --memory 4Gi \
  --cpu 1 \
  --timeout 60s \
  --min 1
```

**Build and deploy music ed agent to Cloud Run** --

```bash
source .env
history_agent_url=$(gcloud run services describe history-agent --project "${GOOGLE_CLOUD_PROJECT}" --region "${GOOGLE_CLOUD_LOCATION}" --format="value(status.url)" -q)
history_agent_card_url="${history_agent_url}/.well-known/agent-card.json"
gcloud run deploy music-ed-agent \
  --source music_ed_agent \
  --region "${GOOGLE_CLOUD_LOCATION}" \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars REMOTE_AGENT_CARD=${history_agent_card_url},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_GENAI_USE_VERTEXAI=true \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 1 \
  --timeout 60s \
  --min 1
```

Open Music Education Agent URL provided by the Cloud Run deployment command for music-ed-agent.
You should be able to see ADK Web UI,
and interact with the Music Education Agent that will call History Agent deployed to another Cloud Run service.
