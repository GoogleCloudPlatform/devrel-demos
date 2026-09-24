# 🌉 Bridge Deck: Complete Human User and Operator Guide

> **Last Updated:** September 18, 2026

Welcome to the **Bridge Deck Human User and Operator Guide**.
This guide provides practical, step-by-step instructions
for pairing with your Antigravity lead engineer (Astra),
navigating the web dashboard, configuring AI engines,
and managing collaborative multi-agent workspaces.

---

## 📑 Table of contents

1.  [How to download, launch, and pair with Astra](#1-how-to-download-launch-and-pair-with-astra)
1.  [How to connect to Google Cloud and verify credentials](#2-how-to-connect-to-google-cloud-and-verify-credentials)
1.  [How to use cores](#3-how-to-use-cores)
1.  [How to sync cores and add models](#4-how-to-sync-cores-and-add-models)
1.  [How to add a team member and craft their personality](#5-how-to-add-a-team-member-and-craft-their-personality)
1.  [How to manage project rooms and assign team members](#6-how-to-manage-project-rooms-and-assign-team-members)
1.  [How to add project directories and scope workspace access](#7-how-to-add-project-directories-and-scope-workspace-access)
1.  [How to assign project roles](#8-how-to-assign-project-roles)
1.  [How to manage agent write permissions](#9-how-to-manage-agent-write-permissions)
1.  [How to deploy and access Bridge Deck on Google Cloud](#10-how-to-deploy-and-access-bridge-deck-on-google-cloud)
1.  [Quick reference Astra prompts](#-quick-reference-astra-prompts)

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

    > *"Please clone `https://github.com/GoogleCloudPlatform/devrel-demos.git`, navigate to `agents/bridge-deck`, create a Python virtual environment, install dependencies, and initialize yourself as Astra using `agents/bridge_deck_lead.json`."*

    Your agent reads `agents/bridge_deck_lead.json`, adopts Astra's personality,
    directives, and tool permissions, and connects to the workspace.

1.  Prompt Astra to verify credentials and launch the app:

    > *"Please verify Google Cloud authentication and launch the Bridge Deck server in the background on port 8080."*

1.  Open your browser and visit [http://localhost:8080](http://localhost:8080).

---

## 2. How to connect to Google Cloud and verify credentials

Bridge Deck uses [**Gemini Enterprise Agent Platform**](https://g.dev/ai/gemini-enterprise-agent-platform)
for frontier model inference
(Gemini 3.7 Flash, Claude Opus 5, and custom GPU endpoints).

Prompt Astra:

> *"Astra, verify my Google Cloud authentication status and check which GCP project ID is configured."*

Astra checks your environment, guides you through Application Default
Credentials (ADC) if needed, and sets your active project.

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

## 4. How to sync cores and add models

Bridge Deck features automatic discovery and synchronization across both cloud and local AI providers.

### Sync models from Google Model Garden

You do not need to manually configure endpoints, temperature settings, or token limits. Bridge Deck automatically discovers and synchronizes frontier models from your Google Cloud project:

1. Under _Cores_ in the left sidebar, click **Google Model Garden**.
2. Click **🔄 Sync with Google Model Garden**.
3. Bridge Deck connects to Vertex AI and registers all active frontier models (including Gemini 3.7 Flash, Claude Opus 5, Gemini 2.5 Pro/Flash, and Gemma).
4. Synchronized models are immediately available when configuring or updating team members.

> **Tip**: You can also simply ask Astra in Antigravity:
> *"Astra, please sync our Google Model Garden models."*

---

### Sync agents from Google ADK and Antigravity

- **Google ADK**: Under _Cores_ in the left sidebar, select **Google ADK** and click **🔄 Sync with Google ADK** to discover and register active ADK agent workflows.
- **Google Antigravity**: Under _Cores_ in the left sidebar, select **Google Antigravity** and click **🔄 Sync with Antigravity** to refresh locally registered Antigravity agents.

---

### Add a local model from Ollama

For local offline inference:

1. Ensure Ollama is running on your workstation and pull your desired model (for example, `ollama pull llama3.3:70b`).
2. Under _Cores_ in the left sidebar, select **Ollama Engine**.
3. Click **➕ Add Model to Core**.
4. Enter the exact model tag (for example, `llama3.3:70b`).
5. Click **Save Model**. The model is immediately available to assign to team members.

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

## 10. How to deploy and access Bridge Deck on Google Cloud

If you deployed the Bridge Deck on Google Cloud (or plan to),
the platform runs on **Google Cloud Run** backed by high-availability GCS FUSE persistent storage
and distributed Cloud Tasks queuing.

### Deploying to Cloud Run
You don't need to run deployment scripts manually. Simply prompt Astra in Antigravity:

> *"Astra, please deploy the Bridge Deck to Google Cloud Run."*

Astra references the deployment protocol in `docs/agent_user_guide.md`, verifies your Google Cloud project credentials, runs the automated pre-flight test gate, executes the rollout, and provides you with your authenticated launch link.

---

### Accessing your cloud deployment
If your Bridge Deck is deployed to Cloud Run, access is gated by Google Cloud IAM. Simply prompt Astra:

> *"Astra, please connect to the live Cloud Run service and open the Bridge Deck."*

Astra automatically fetches the latest token from Secret Manager, starts the authenticated IAM proxy tunnel, and opens the live dashboard in your browser.

---

### Synchronizing disaster recovery backup depot
If you configured a cold backup repository (`${BACKUP_REPO_URL}`), you can ask Astra to verify or synchronize the mirror:

> *"Astra, please run a dry-run check on our disaster recovery backup depot."*

Or to perform the sync:

> *"Astra, please synchronize our disaster recovery backup depot."*

---

## 💬 Quick reference Astra prompts

You don't need to memorize terminal commands or run shell scripts. You can copy and paste any of these everyday prompts directly to Astra in Antigravity:

### Local development and testing
- **Launch Local Bridge Deck**:
  > *"Astra, please launch the Bridge Deck server in the background on port 8080."*
- **Run Full Automated Test Suite**:
  > *"Astra, please run the full automated test suite and report any issues."*
- **Check System & Credentials**:
  > *"Astra, verify my Google Cloud authentication status and configured GCP project."*

### Google Cloud operations
- **Deploy to Google Cloud Run**:
  > *"Astra, please deploy the Bridge Deck to Google Cloud Run."*
- **Open Live Cloud Dashboard**:
  > *"Astra, please connect to the live Cloud Run service and open the Bridge Deck in my browser."*
- **Sync Cold Disaster Recovery Backup**:
  > *"Astra, please synchronize our disaster recovery backup depot."*

---

*Bridge Deck is designed for seamless, multi-vendor AI collaboration
with principled governance, complete epistemic grounding,
and zero-build ease of use.* 🌉✨
