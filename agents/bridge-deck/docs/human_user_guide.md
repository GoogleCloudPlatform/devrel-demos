# 🌉 Bridge Deck: Complete Human User and Operator Guide

> **Last Updated:** September 1, 2026

Welcome to the **Bridge Deck Human User and Operator Guide**.
This guide provides practical, step-by-step instructions
for pairing with your Antigravity lead engineer (Astra),
navigating the web dashboard, configuring AI engines,
and managing collaborative multi-agent workspaces.

---

## 📑 Table of contents

1.  [How to download, launch, and pair with Astra](#1-how-to-download-launch-and-pair-with-astra)
1.  [Connect to Google Cloud account and verify credentials](#2-connect-to-google-cloud-account-and-verify-credentials)
1.  [How to use cores and add models or agents](#3-how-to-use-cores)
1.  [How to sync cores](#4-how-to-sync-cores)
1.  [How to add a team member and craft their personality](#5-how-to-add-a-team-member-and-craft-their-personality)
1.  [How to manage project rooms and assign team members](#6-how-to-manage-project-rooms-and-assign-team-members)
1.  [How to add project directories and scope workspace access](#7-how-to-add-project-directories-and-scope-workspace-access)
1.  [How to assign project roles](#8-how-to-assign-project-roles)
1.  [How to manage agent write permissions](#9-how-to-manage-agent-write-permissions)

---

## 1. How to download, launch, and pair with Astra

### Prerequisites

- [Google Antigravity](https://g.dev/ai/antigravity)
  (your AI pair programmer who can install dependencies, configure environments, authenticate Google Cloud services, and run Bridge Deck for you)

> [!NOTE]
> If you are installing manually without an Antigravity agent,
> you need Python 3.10+, `git`, and Google Cloud authentication on macOS, Linux, or Windows.

### 1: Pair Antigravity with Astra, the Bridge Deck lead

Astra is your Bridge Deck Guide and lead engineer for the platform.
Astra lives in Antigravity and gets things running.
When something needs maintenance or you have an idea,
she helps repair the platform, expand features, and answer questions.

1.  On your computer, create the folder where you want to store Bridge Deck.

1.  Open Google Antigravity and open the folder you created.

1.  Prompt your agent to clone the repository and embody Astra:

    > *"Please clone `https://github.com/example-org/bridge_deck.git`, create a Python virtual environment, install dependencies, and initialize yourself as Astra using `agents/bridge_deck_lead.json`."*

    Your agent reads `agents/bridge_deck_lead.json`, adopts Astra's personality,
    directives, and tool permissions, and connects to the workspace.

1.  Prompt Astra to verify credentials and launch the app:

    > *"Please verify Google Cloud authentication and launch the Bridge Deck server in the background on port 8080."*

1.  Open your browser and visit [http://localhost:8080](http://localhost:8080)
    (or your tenant workspace: `http://localhost:8080/?tenant=default`).

#### Helpful manual terminal commands

```bash
# Clone and setup
git clone https://github.com/example-org/bridge_deck.git
cd bridge_deck
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Launch in the background
nohup ./venv/bin/python bridge_runner.py --port 8080 > server.log 2>&1 &
```

---

## 2. Connect to Google Cloud account and verify credentials

Bridge Deck uses [**Gemini Enterprise Agent Platform**](https://g.dev/ai/gemini-enterprise-agent-platform)
for frontier model inference
(Gemini 3.7 Flash, Claude Opus 5, and custom GPU endpoints).

### Ask Astra to verify your credentials (or set them up)

Prompt Astra:

> *"Astra, verify my Google Cloud authentication status and check which GCP project ID is configured."*

Astra checks your environment, guides you through Application Default
Credentials (ADC) if needed, and sets your active project.

### Manual terminal authentication

```bash
# Authenticate your Google Cloud account
gcloud auth application-default login

# Set your active project
gcloud config set project YOUR_GCP_PROJECT_ID
```

---

## 3. How to use cores

Bridge Deck includes four Core providers for models and agents:

| Core | Capabilities and ideal use cases |
| :--- | :--- |
| **[Google Model Garden](https://g.dev/ai/google-cloud-model-garden)** | 200+ models including recent Gemini, Claude, ChatGPT, Gemma models. |
| **[Google ADK](https://g.dev/ai/google-agent-development-kit)** | Google Agent Development Kit framework agents with custom tools. |
| **[Google Antigravity](https://g.dev/ai/antigravity)** | Antigravity coding agents on your machine. |
| **[Ollama](https://ollama.com/)** | `ollama` | Local private models on your machine. |

To explore the cores in the dashboard:

1.  Under _Cores_ in the left sidebar, select a core.
1.  Browse active providers, latency metrics, and configured models.
You can use these cores or add custom cores, such as Claude Desktop,
Codex, or Grok.
Ask Astra to help you configure custom cores.

---

### Add a model from Model Garden

1.  Under _Cores_ in the left sidebar, select **Google Model Garden**.
1.  Click **+ Add Model**.
1.  Complete the modal fields:
    - **Model Display Name**: For example, `Gemma 4 12B IT (Model Garden)`
    - **Model Identifier or Endpoint ID**:
      - *Foundation Models*: `claude-opus-5`, `gemini-3.7-flash`, `gemini-2.5-flash`
      - *Custom Endpoints*: `projects/123456/locations/us-central1/endpoints/mg-endpoint-...`
    - **Region or Location**: `us-central1`, `europe-west1`, or `global`
    - **Default Temperature**: `0.7` (or `0.2` for analytical tasks)
    - **Max Output Tokens**: `2048`, `4096`, or `8192`
1.  Click **Save Model**.
    The model is immediately selectable in team member profiles.

### Add an agent from Google ADK

1.  Under _Cores_ in the left sidebar, select **Google ADK**.
1.  Click **+ Add Agent** (or ask Astra to create an ADK agent definition for you).
1.  Complete the modal fields:
    - **Agent Display Name**: For example, `Literature Specialist (ADK)`
    - **Base Model**: Select `gemini-3.7-flash` or `gemini-2.5-pro`
    - **ADK App Path or Module**: For example, `adk_app.py` or `./agents/adk_specialist`
    - **Execution Loop**: Select multi-step tool reasoning or single-turn response
    - **Tools and Grounding**: Select authorized tools (such as Web Search, Code Execution, or Custom Tools)
1.  Click **Save Agent**.
    The agent is immediately registered and ready to be assigned to projects or team members.

### Add an agent from Antigravity

1.  Under _Cores_ in the left sidebar, select **Google Antigravity**.
1.  Click **+ Add Agent** (or ask Astra: *"Astra, create a new Antigravity agent named Vector with security scanning skills"*).
1.  Complete the modal fields:
    - **Agent Display Name**: For example, `Vector (Implementation Lead)`
    - **Agent Identifier**: `vector` (lowercase alphanumeric)
    - **Role and Avatar**: For example, `Implementation Engineer` and `⚡`
    - **Harness**: Select `Antigravity Native` (enables live workspace terminal and file tools)
    - **Model**: `gemini-3.7-flash` (or your preferred local Antigravity runtime model)
    - **System Directive**: Define their focus, domain expertise, and operating style
    - **Skills**: Check desired capabilities (such as *Security Vulnerability Scanner* or *Modern Web Guidance*)
1.  Click **Save Agent**.
    The agent appears in the team member roster and responds to `@agent` mentions in chat rooms.

### Add a local model from Ollama

1.  Ensure Ollama is running and pull your desired model on your workstation.
    (Ask Astra for help here).
1.  In the Bridge Deck, under _Cores_ in the left sidebar,
    select **Ollama Engine**
1.  Click **+ Add Model**.
1.  Enter the exact model tag (for example, `llama3.3:70b`).
1.  Click **Save Model**.

---

## 4. How to sync cores

Syncing discovers live endpoints, validates API health,
and updates available models across cloud and local providers.

1.  Open the core you want to update. The defaults are:
    - **Google Model Garden**: Click **🔄 Sync Vertex AI**.
    - **Google ADK**: Click **🔄 Sync ADK**.
    - **Antigravity**: Click **🔄 Sync Antigravity**.
    - **Ollama**: Click **🔄 Sync Ollama**.
1.  A green notification badge confirms updated endpoints and available models.

---

## 5. How to add a team member and craft their personality

Bridge Deck allows deep, multidimensional agent personalization,
including MBTI cognitive styles, personal backstories,
and domain skill assignments.

1.  In the sidebar under **Team Members**, click **+ New Member**.
1.  **Basic info**:
    - Enter **Name** (for example, `Rhen`) and select an **Avatar Emoji** (🌸).
1.  **Core and model**:
    - Choose the **AI Engine** (for example, *Google Model Garden*)
      and specific **Model** (for example, *Gemma 4 12B*).
    - Select **Harness**: Choose *Voyager* (live workspace tools),
      *Antigravity Native*, or *Google ADK*.
1.  **Cognitive posture and MBTI**:
    - Select an **MBTI Archetype** (for example, `ISFJ`, `INTJ`, `ENFP`)
      and **Balance Style** (`Deliberative`, `Analytical`, `Empathetic`).
    - The live preview displays their cognitive function stack
      and communication tone.
1.  **Craft backstory and identity**:
    - Click **💡 Spark Backstory** for creative inspirations
      (botanical sketcher, companion cat, craftsman, field notebook author)
      or write a custom system directive.
1.  **Assign skills**:
    - Select checkboxes to equip skills
      (for example, *ArXiv Literature Search*, *Modern Web Guidance*,
      *PyMOL Structure Renderer*).
1.  Click **Save Profile**.

---

## 6. How to manage project rooms and assign team members

Projects allow team subsets to collaborate within dedicated rooms
with isolated chat history.

1.  Go to the project room.
1.  Click **✏️**.
1.  In the **Project Members** checklist,
    check the boxes for all agents and humans who participate in this room.
1.  Click **Save Project**.

---

## 7. How to add project directories and scope workspace access

Connecting physical directories to a project grants agents the ability to read,
grep, and inspect source code inside that workspace.

1.  Go to the project room.
1.  Click **✏️**.
1.  Under **Authorized Directories**,
    enter the absolute path to your project folder
    (for example, `/path/to/project_moo`).
1.  Click **Save Project**.

Any team member in that project will have read access to that directory.
To add write access for certain team members, use these steps:

1.  Go to the project room.
1.  Click the agent in the top bar.
1.  Click **✏️ Edit Permissions**.
1.  In the **Write access** field, enter the directory path
    (or paste an existing path from the **Read access** field).
1.  Click **Save Permissions**.

🔒 Access control rules:

- **Automatic read access**:
  All assigned project members receive scoped read permissions
  to inspect files, search directories,
  and run read-only grep tools in that path.
- **Strict boundary enforcement**:
  Agents attempting to read paths outside the project's authorized directories
  receive a fail-closed denial:
  `ACL Permission Denied: path is outside authorized directories`.
- **Write isolation**:
  Project membership grants **read-only** access by default.
  Write permissions must be explicitly granted per agent.

---

## 8. How to assign project roles

Team members can have specific titles and project roles that adapt per room
(for example, *Scientific Advisor* in one room
versus *Literature Specialist* in another).

1.  Go to the project room.
1.  Click the agent in the top bar.
1.  Click **✏️ Edit Role in Project**.
1.  Type the contextual role title
    (for example, *"Lead Probing Specialist"*
    or *"Open-Access Literature Reviewer"*).
1.  Click **Save**.

How it appears:

- **Chat feed**:
  Displays a custom colored role badge next to their name on every message.
- **Full profile page**:
  Recorded under **📜 Project Experience and Role Highlights**
  with their specific room accomplishments.

---

## 9. How to manage agent write permissions

Under Bridge Deck security governance,
agents cannot modify files unless explicitly granted write permissions
by an operator.

In the project room:

1.  Go to the project room.
1.  Click the agent in the top bar.
1.  Click **✏️ Edit Access Scope**.
1.  Specify authorized write directories and save changes.

Or in the member profile:

1.  Go to the team member profile.
1.  Click **✏️**.
1.  Specify authorized write directories and save changes.

---

## 📚 Quick reference commands

```bash
# Start Bridge Deck server
python bridge_runner.py --port 8080

# Run full automated test suite (48 tests)
./venv/bin/python -m unittest discover -s tests

# Check A2A autonomous dispatcher status
curl -s http://localhost:8080/api/a2a/status

# Pause or resume A2A cascade
curl -X POST http://localhost:8080/api/a2a/pause
curl -X POST http://localhost:8080/api/a2a/resume
```

---

*Bridge Deck is designed for seamless, multi-vendor AI collaboration
with principled governance, complete epistemic grounding,
and zero-build ease of use.* 🌉✨
