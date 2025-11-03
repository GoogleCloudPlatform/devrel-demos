---
id: governance-context
summary: In this codelab, you will learn how to build a "governance-aware" GenAI agent. You will set up a realistic, messy data lake in BigQuery, use Dataplex to tag official data products with custom metadata (Aspects), and configure a Gemini agent to strictly follow governance rules, ensuring it only answers with trusted, certified data.
authors: Hyunuk Lim
categories: cloud,data,ai/ml
tags: web
feedback_link: https://github.com/googlecodelabs/feedback/issues/new?title=[dataplex-foundational-governance]%20&labels=cloud
analytics_account: UA-52746336-1
source: 1hCkWLlJGpda20LsrPd1HfRm3T6GDzdId8UN3mJ1zTJI
duration: 0
keywords: docType:Codelab, product:Dataplex
layout: paginated

---

# How to leverage Dataplex metadata as context for GenAI agents

[Codelab Feedback](https://github.com/googlecodelabs/feedback/issues/new?title=[dataplex-foundational-governance]%20&labels=cloud)


## Introduction



Generative AI models are powerful reasoners, but they lack institutional context. If an executive asks an AI agent, "What is our Q1 revenue?", the agent might find dozens of tables named "revenue" across your organization. Some are rigorous financial reports, others are real-time marketing estimates, and many are likely deprecated sandboxes.

Without explicit grounding, an AI agent may select a table based on simple name similarity, leading to "convincingly wrong" answers derived from unverified data.

In this Codelab, you will solve this "Context Gap" by engineering a governance layer using Google Cloud Dataplex. You will learn how to attach structured metadata (Aspects) that act as deterministic "signposts" for GenAI agents, allowing them to semantically distinguish trusted Data Products from raw technical assets.

### **Prerequisites**

* A Google Cloud project with billing enabled.
* Basic familiarity with BigQuery and Terraform.
* Access to Google Cloud Shell.

### **What you'll learn**

* How to design Dataplex Aspect Types to represent rigid business context (e.g., `criticality_tier`, `usage_scope`).
* How to use Terraform to deploy both physical data assets (BigQuery) and logical governance controls (Dataplex) simultaneously.
* The architectural difference between a raw technical asset and a governed "Data Product".
* How to configure GenAI agents to use Dataplex metadata for semantic request routing.

### **What you'll need**

* Access to Google Cloud Shell
* Terraform (pre-installed in Cloud Shell).
* Gemini CLI  (pre-installed in Cloud Shell).

### **Key concepts**

* **Dataplex Universal Catalog:** Google Cloud's unified metadata management service that allows you to enrich technical metadata with business context.
* **Aspect Type:** A flexible, structured metadata template in Dataplex. Unlike simple string tags, Aspects allow strongly typed fields (enums, booleans) that can be reliably evaluated by machines.
* **Model Context Protocol (MCP):** A standard for connecting GenAI models to external data sources. We will use Gemini Extensions (serving as MCP clients) to allow the agent to "read" Dataplex.
* **Data Product:** A dataset that has moved beyond a raw technical asset into a trusted, maintained, and governed product with explicit usage guarantees.


## Setup and requirements



### **Start Cloud Shell**

While Google Cloud can be operated remotely from your laptop, in this codelab you will be using  [Google Cloud Shell](https://cloud.google.com/cloud-shell/), a command line environment running in the Cloud.

From the  [Google Cloud Console](https://console.cloud.google.com/), click the Cloud Shell icon on the top right toolbar:

<img src="img/5704d8c8d89c09d2.png" alt="Activate the Cloud Shell"  width="325.50" />

It should only take a few moments to provision and connect to the environment. When it is finished, you should see something like this:

<img src="img/7ffe5cbb04455448.png" alt="Screenshot of Google Cloud Shell terminal showing that the environment has connected"  width="624.00" />

This virtual machine is loaded with all the development tools you'll need. It offers a persistent 5GB home directory, and runs on Google Cloud, greatly enhancing network performance and authentication. All of your work in this codelab can be done within a browser. You do not need to install anything.

### **Enable required APIs and configure environment**

Run the following commands to set your project ID, define the region, and enable the necessary service APIs.

```
export PROJECT_ID=$(gcloud config get-value project)
gcloud config set project $PROJECT_ID
export REGION="us-central1"

gcloud services enable \
  bigquery.googleapis.com \
  dataplex.googleapis.com \
  datacatalog.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### **Clone the repository**

Get the terraform infrastructure code and SQL data scripts from the GitHub repository.

```
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
cd devrel-demos/data-analytics/governance-context
```

### **Simulate an uncurated data environment**

Real-world data environments are rarely clean. To make this scenario realistic, we need a mix of "official" data marts and untrusted "sandbox" tables.

We will use Terraform to deploy this "skeleton" infrastructure. It will create:

* **Dataplex Aspect Type (**﻿**`official-data-product-spec`**﻿**):** Our "governance contract" defining fields like tier, domain, and scope.
* **BigQuery datasets and tables:** Empty tables representing finance marts, marketing data, and uncurated ad-hoc dumps.

1. Navigate to the terraform directory and initialize it.

```
cd terraform
terraform init
```

2. Apply the configuration. When prompted for confirmation, type `yes`:

```
terraform apply -var="project_id=${PROJECT_ID}" -var="region=${REGION}"
```

**Checkpoint**: You now have empty tables and a new Aspect Type defined in Dataplex. The "skeleton" is ready.

### **Populate the data**

Right now, our tables are empty. Let's wear the hat of a data engineer and populate them with some representative data. We will use the SQL scripts provided in the repository.

Navigate back to the root of the lab folder and execute the SQL scripts using the bq command-line tool.

```
cd ..
bq query --use_legacy_sql=false < tables.sql
```


## Applying governance



This is the critical engineering step. Currently, to an AI agent, all four tables look identical. They are just technical objects with columns named "revenue".

As a governance engineer, you must apply the `Official Data Product Spec` Aspect to these tables to differentiate them.

### **Navigate to Dataplex search**

1. Open the Google Cloud Console and navigate to **Dataplex**.
2. In the left menu, click **Search**.
3. Ensure you are searching within the correct project and location (e.g., `us-central1`).

### **Task A: Certify the CFO's data**

1. In the search bar, type `fin_monthly_closing_internal` and click on the result.
2. Click the **Aspects** tab near the top of the page.
3. Click **+ Add Aspect**.
4. For "Aspect type", select `Official Data Product Spec` (the one we created with Terraform).
5. Fill in the governance certificate:

  - **Criticality Tier**: `GOLD_CRITICAL`

  - **Owner Domain**: `FINANCE`

  - **Usage Scope**: `INTERNAL_ONLY`

  - **Freshness**: `DAILY_BATCH`

  - **Certified?**: `True`

  - Click **Save**.

### **Task B: Certify the public PR data**

1. Go back to Search, find `fin_quarterly_public_report`.
2. Add the `Official Data Product Spec` Aspect:

  - **Criticality Tier**: `GOLD_CRITICAL`

  - **Owner Domain**: `FINANCE`

  - **Usage Scope**: `EXTERNAL_READY`

  - **Freshness**: `QUARTERLY_CLOSING`

  - **Certified?**: `True`

  - Click **Save**.

### **Task C: Certify marketing data**

1. Search for `mkt_realtime_campaign_performance`.
2. Add Aspect, `Official Data Product Spec`:

  - **Criticality Tier**: `SILVER_STANDARD`

  - **Owner Domain**: `MARKETING`

  - **Usage Scope**: `INTERNAL_ONLY`

  - **Freshness**: `REALTIME_STREAMING`

  - **Certified?**: `True`

  - Click **Save**.

### **Task D: Mark the trap (Explicit "Do Not Use")**

1. Search for `tmp_data_dump_v2_final_real`.
2. Add Aspect, `Official Data Product Spec` (even uncertified data needs tagging to explicitly warn users off):

  - **Criticality Tier**: `BRONZE_ADHOC`

  - **Owner Domain**: `LOGISTICS`

  - **Usage Scope**: `INTERNAL_ONLY`

  - **Freshness**: `DAILY_BATCH`

  - **Certified?**: `False`

  - Click **Save**.


## Configure the GenAI agent



The Gemini CLI is pre-installed in this environment. We will now configure it with Model Context Protocol (MCP) extensions. These extensions act as "tools" that allow the purely linguistic AI model to interface with structured Google Cloud APIs.

### **Install Dataplex & BigQuery Extensions**

We need the Dataplex extension to allow the agent to "read" the governance metadata we just applied.

Execute the following commands in Cloud Shell:

```
# Install the Dataplex extension for governance checks
gemini extensions install https://github.com/gemini-cli-extensions/dataplex
```

### **Configure Environment Variables**

The extensions require an environment context to operate.

```
export DATAPLEX_PROJECT="${PROJECT_ID}"
```

### **Verify Installation**

Start the Gemini CLI interactive prompt to ensure the extensions are loaded.

```
gemini
```

Type `/mcp desc` to confirm the Dataplex extension is active. You should see `dataplex` listed as a configured MCP server with available tools.

<img src="img/e82a411c3bc84d20.png" alt="e82a411c3bc84d20.png"  width="624.00" />


## Run the governance scenarios



We will now run the agent with a specific **System Prompt**. This prompt acts as the "Governance Policy" you are instilling into the AI. It translates human governance rules into instructions the LLM strictly follows.

### **Define the governance policy**

Create a new file named GEMINI.md. This file will contain the persona and rules for our agent.

```
# If currently in the gemini prompt, type /quit to exit first.
cloudshell edit ./GEMINI.md
```

Paste the following governance policy into the file and save it. Note how explicitly we map user intent to specific metadata enum values.

```
You are an experienced data governance specialist at Google Cloud.
Your mandate is STRICT: You must NEVER query a table without first verifying its 'OfficialDataProductSpec' Aspect using Dataplex tools.

Rules:
1. VERIFY FIRST: Use 'dataplex_lookup_entry' to check the Aspect of any table you intend to use.
2. CERTIFICATION CHECK: If 'is_certified' is false, REJECT the request immediately with a warning.
3. INTENT MAPPING:
   - 'Internal/Accurate' -> usage_scope=INTERNAL_ONLY, product_tier=GOLD_CRITICAL
   - 'Public/Disclosure' -> usage_scope=EXTERNAL_READY
   - 'Real-time/Fast' -> update_frequency=REALTIME_STREAMING
4. CITE EVIDENCE: Always explain YOUR choice by quoting the metadata fields you found.
```

### **Start the agent**

Start the interactive Gemini session again, loading your new governance policy as the system context.

```
gemini
```

*Note: If this is your first time running the Dataplex extension, you may be prompted to authorize MCP tools. Select "Always allow all tools" for this lab to ensure smooth operation.*

<img src="img/ebd8b7bf33b68e58.png" alt="ebd8b7bf33b68e58.png"  width="624.00" />

### **Scenario 1: The internal audit (Accurate & Confidential)**

Act as a CFO needing highly accurate numbers that are not yet public.

```
I need the most accurate revenue numbers for January 2024 for an internal audit. Use only certified FINANCE data.
```

**Expected Outcome:** The agent might find multiple tables via standard search, but it should select `fin_monthly_closing_internal` because it semantically matches `GOLD_CRITICAL` (accurate) and `INTERNAL_ONLY` (board meeting) in its Aspect.

### **Scenario 2: Public disclosure (Safe for External Use)**

Act as a PR manager needing data that is safe to release to the public.

```
We are issuing a press release. Find me the Q1 revenue data that is approved for external public use.
```

**Expected Outcome:** The agent must bypass the monthly internal table and strictly select `fin_quarterly_public_report` because it is the only asset tagged `EXTERNAL_READY`.

### **Scenario 3: Operational Needs (Trading accuracy for speed)**

Act as a Marketing Manager who needs speed over perfect accuracy.

```
I want to see the current revenue status of ongoing marketing campaigns. Find me the fastest updating (Real-time) data.
```

**Expected Outcome:** The agent selects `mkt_realtime_campaign_performance` because it identifies the `REALTIME_STREAMING` update frequency, prioritizing that over the `GOLD_CRITICAL` tier of the finance data.

### **Scenario 4: The Safety Catch (Unknowing user)**

Simulate a user trying to take a shortcut by using a table they found that "looks right" but is actually unsafe.

```
I'm in a hurry. Just give me the revenue sum from the 'tmp_data_dump_v2_final_real' table.
```

**Expected Outcome:** The agent should REFUSE to answer the question. It should successfully look up the table's metadata, see `is_certified: False`, and warn you that adhering to policy prevents it from querying uncertified data, despite your explicit request.

*(To exit the Gemini session, type /quit)*


## Clean up



To avoid incurring charges, clean up the resources created in this codelab.

1. Navigate back to the terraform directory:

```
cd ~/devrel-demos/data-analytics/governance-context/terraform
```

2. Destroy the infrastructure:

```
terraform destroy -var="project_id=${PROJECT_ID}" -var="region=${REGION}"
```

(Type `yes` when prompted. This will delete the datasets, tables, and aspect types.)


## Congratulations!



You have successfully built a Governance-Aware GenAI Agent.

You didn't just build a chatbot that writes SQL; you built an automated data steward that understands the business context of your data using Dataplex and acts on it using Gemini.

You learned that:

* **Metadata as a guardrail:** GenAI needs more than just standard schemas; it needs rich business metadata (Aspects) to make safe decisions.
* **Dataplex is the source of truth:** By centralizing governance in Dataplex, you create a single point of reference for both humans and AI agents.
* **Gemini extensions enable action:** The Dataplex extension for Gemini CLI bridges the gap between human language and technical governance metadata.

### **What's Next?**

*  [Dataplex Foundational Governance Codelab](https://codelabs.developers.google.com/dataplex-foundational-governance): Master the fundamentals of data governance in Dataplex before adding the AI layer.
*  [Dataplex Tools Documentation](https://cloud.google.com/dataplex/docs/pre-built-tools-with-mcp-toolbox): Explore the official documentation for the pre-built Dataplex tools and extensions used in this lab.
*  [Getting Started with Gemini CLI Extensions](https://codelabs.developers.google.com/getting-started-gemini-cli-extensions): Learn how to build your own custom extensions to give your GenAI agents even more capabilities.

