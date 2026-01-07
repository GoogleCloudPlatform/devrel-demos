# 🐍 Python Tutor - ADK State and Memory Example 🗳️

This project contains a **Python programming tutor** sample agent built with [ADK Python](https://google.github.io/adk-docs/). 

This sample agent was built to show how you can integrate state and memory into your AI agent to improve the agent's responses, and add personalization. This Python Tutor agent introduces concept of Python **[dictionaries](https://www.w3schools.com/python/python_dictionaries.asp)**, then runs the user through a simple, 4-question quiz. 


There are two variations of the Python tutor agent in this directory. 
1. **python_tutor_short_term** makes use of just ADK session state, with options for in-memory session storage, and DB session storage via sqlite. The user's name and quiz progress is stored in the state. 
2. **python_tutor_long_term** - Builds on the short-term memory agent by adding a long-term memory store, via [Vertex AI Memory Bank](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview), accessed through Agent Engine. Some important notes about this setup:
   - [Vertex AI Memory Bank](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview) is a feature of Agent Engine, but you *do not* need to actually run your ADK agent on Agent Engine. All you need is a "stub" Agent Engine instance with an ID. You can run the agent locally or deploy it to Cloud Run. 


---

## Directory Structure

 `python_tutor_long_term` and `python_tutor_short_term` are separate agent implementations that don't rely on each other. Shared prompts and tools are stored in the `python_tutor_core` directory, and both agents make use of the core functionality. 

```
.
├── python_tutor_core
│   ├── agent_utils.py
│   └── prompts.py
├── python_tutor_long_term
│   ├── agent.py
│   └── memory_tools.py
│   ├── python_tutor_core -> ../python_tutor_core
│   └── tools -> ../tools
├── python_tutor_short_term
│   └── agent.py
│   ├── python_tutor_core -> ../python_tutor_core
│   └── tools -> ../tools
└── tools
    └── tools.py
```

## Run Locally 

For both flavors of this agent, you will need: 
- A terminal
- Git
- Python 3.10+ 
- [uv](https://docs.astral.sh/uv/getting-started/installation/) 

Clone this repository and navigate to this subdirectory, before getting started: 

```bash 
git clone https://github.com/GoogleCloudPlatform/devrel-demos 
cd devrel-demos/ai-ml/python-tutor
```

### Short-term memory agent (Persist Sessions)

<img src="images/st_arch_diagram.png" style="width: 50%; height: 50%"/>​


This agent simply stores session data (eg. state fields) to a local database, for inspection. This means you can close the ADK Web browser tab, open a new tab, and be able to restore your session. You can even shut down `adk web` and restart it - because you're persisting the session data locally. What this agent does *not* support are user preferences across multiple sessions - that's what the long-term agent will cover below. This agent can only remember what happens **within** the same session.

With both flavors, navigate to `127.0.0.1:8000` and make sure you select `python_tutor_short_term` from the drop-down, before talking with the agent. Have the agent walk you through a quiz, then inspect the session and state data. 


#### With sqlite 

Stores session data to a local file: `pythontutor_sessions.db` 

```bash
uv run adk web --session_service_uri="sqlite:///./pythontutor_sessions.db" 
```

You can inspect the sqlite session data file by adding an IDE extension for SQLite, and then opening the `pythontutor_sessions.db` file: 

![](images/sqlite_state_inspection.png)

#### With PostgreSQL

Stores session data to a local or remote PostgreSQL database. 
Note you need to run `CREATE_DATABASE pythontutor` first. 

```bash
uv run adk web --session_service_uri="postgresql://postgres:admin@127.0.0.1:5432/pythontutor" 
```

After you chat with the agent and run through the quiz, you can inspect the session state through the `psql` command line:

```bash
psql --u postgres
```

Then: 

```
\c pythontutor;
\dt;
```

*Expected output*:

```sql
            List of relations
 Schema |    Name     | Type  |  Owner
--------+-------------+-------+----------
 public | app_states  | table | postgres
 public | events      | table | postgres
 public | sessions    | table | postgres
 public | user_states | table | postgres
(4 rows)
```

```bash
SELECT * FROM sessions; 
```

*Expected output*: 

```sql
       app_name         | user_id |                  id                  |                                                                      state                                                                       |        create_time         |        update_time
-------------------------+---------+--------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------+----------------------------+----------------------------
 python_tutor_short_term | user    | 09220dfe-4ab6-4079-9865-f672dc5009be | {"quiz_started": true, "total_answered": 2, "correct_answers": 1, "quiz_initialized": true, "score_percentage": 50, "current_question_index": 2} | 2025-07-14 10:01:13.174634 | 2025-07-14 10:01:31.715883
(1 row)
```

Note the session ID (`09220dfe` - yours will be different!), and the various state fields (e.g., `correct_answers` and `current_questionIndex`). 

### Long-term memory agent (with Vertex AI Memory Bank)

<img src="images/lt_arch_diagram.png" style="width: 50%; height: 50%"/>​


**Prerequisites**: 
- A Google Cloud project with Billing enabled.
- Python 3.10+ 

1. Open a new terminal tab and set the following environment variables. Replace the placeholder values with your Google Cloud project ID and location.

    ```bash
    export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="your-gcp-location" # e.g., us-central1
    ```

    *Note*: You can find the regions that support Vertex AI Memory Bank in the [official documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview#supported-regions).

2. Install the Vertex AI SDK for Python. 

    ```bash
    pip install --upgrade --quiet google-cloud-aiplatform
    ```

3. Open a Python notebook or interpreter. Run the following Python code to create a new Agent Engine instance.  

    ```python
    from vertexai import agent_engines

    python_tutor_agent_engine = agent_engines.create(display_name='python-tutor-memory-bank')
    ```

    *Expected output*: 

    ```bash
    AgentEngine created. Resource name: projects/477267821782/locations/us-central1/reasoningEngines/123...
    To use this AgentEngine in another session:
    agent_engine = vertexai.agent_engines.get('projects/477267821782/locations/us-central1/reasoningEngines/123...')
    ```

4. Grab the Agent Engine resource **id** (the digits following `reasoningEngines/`) and save it as an environment variable. 
    ```
    # Replace with your ID 
    export AGENT_ENGINE_ID="123456789"
    ```

5. Run the ADK web UI. 

    ```bash
    uv run adk web --session_service_uri="sqlite:///./pythontutor_sessions.db" --memory_service_uri="agentengine://$AGENT_ENGINE_ID"
    ```

    Run through the quiz once, stating your first name beforehand. Then start a new session, and use the same first name. The agent should remember your score from the previous session, by fetching memories from Memory Bank: 

    ![](images/lt_memory_remembers.png)

## Deployment

The agent can be deployed to a scalable, serverless environment on **Vertex AI Agent Engine**.

1.  First, set the required environment variables. If you already set these when running the agent locally, you may only need to add the `GOOGLE_CLOUD_STORAGE_BUCKET`.

    ```bash
    export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="your-gcp-location" # e.g., us-central1
    export GOOGLE_CLOUD_STORAGE_BUCKET="your-gcs-bucket-for-staging" # e.g., gs://agent-engines-deployment
    ```

    *Note*: The staging bucket must exist before you can deploy.

2.  Run the `adk deploy` command for the agent you wish to deploy.

    **(1) Short-term memory agent**

    ```bash
    uv run adk deploy agent_engine \
        --project $GOOGLE_CLOUD_PROJECT \
        --region $GOOGLE_CLOUD_LOCATION \
        --staging_bucket $GOOGLE_CLOUD_STORAGE_BUCKET \
        --trace_to_cloud python_tutor_short_term
    ```

    **(2) Long-term memory agent**

    ```bash
    uv run adk deploy agent_engine \
        --project $GOOGLE_CLOUD_PROJECT \
        --region $GOOGLE_CLOUD_LOCATION \
        --staging_bucket $GOOGLE_CLOUD_STORAGE_BUCKET \
        --trace_to_cloud python_tutor_long_term
    ```
