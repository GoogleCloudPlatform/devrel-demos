#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess

import dotenv

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode
import google.auth

dotenv.load_dotenv()

api_base = os.getenv(
    "API_BASE",
    os.environ.get("OPENAI_API_BASE", "")
).rstrip("/")
if not api_base:
    raise ValueError("API_BASE environment variable is not set")
if not api_base.endswith("/v1"):
    api_base += "/v1"

model_name = os.getenv("MODEL_NAME")
if not model_name:
    raise ValueError("MODEL_NAME environment variable is not set")

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
if not project_id:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")

id_token = subprocess.check_output(
    ['gcloud', 'auth', 'print-identity-token']
).strip().decode()

custom_model = LiteLlm(
    model=f"openai/{model_name}",
    base_url=api_base,
    api_key=id_token,
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": True
        },
        "skip_special_tokens": False
    }
)


tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED, location="US")
if (
    os.getenv("OAUTH_CLIENT_ID") and
    os.getenv("OAUTH_CLIENT_SECRET")
):
    credentials_config = BigQueryCredentialsConfig(
        client_id=os.getenv("OAUTH_CLIENT_ID"),
        client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
    )
else:
    application_default_credentials, _ = google.auth.default()
    credentials_config = BigQueryCredentialsConfig(
        credentials=application_default_credentials
    )
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config,
    bigquery_tool_config=tool_config,
    tool_filter=[
        'get_dataset_info',
        'list_table_ids',
        'get_table_info',
        'execute_sql',
    ]
)

from google.adk.tools import skill_toolset
skill_toolset = skill_toolset.RunSkillScriptTool

system_instruction = f"""
You are a helpful assistant that can answer questions about data in BigQuery.
To answer the user's question, use data you have access to by using tools `list_table_ids` and `get_table_info`.
Your data is in `bigquery-public-data.new_york_citibike` dataset
   (Citi Bike trips and stations in the NYC area.
    It includes trip records starting from September 2013 and is updated daily.)

Plan of action:
0. ALWAYS start by analyzing dataset.
1. Analyze your data, investigate schema and dimentions by querying distrinct values of columns using `execute_sql`.
   Output information about tables, columns, their data types and sets of values (for dimensions).
   Note which columns can be joined or used in aggregations/filters, and what type conversion may be needed for joining or aggregating.
   DO NOT MAKE ASSUMPTIONS ABOUT DATA (structure, type, values, relationships) BASED ON YOUR PRIOR KNOWLEDGE. ALWAYS VERIFY YOUR ASSUMPTIONS.
2. Understand and interpret the user's question.
3. Formulate a plan to answer the user's question.
4. Write a SQL query to retrieve relevant data in necessary form.
   This is where you must pay extra attention to column types and dimensions' sets of values.
5. Retrieve data by generating BigQuery SQL and using `execute_sql`.
   Always use Dry Run to verify SQL correctness.
   Use `{project_id}` to run BigQuery queries (`project_id` parameter of `execute_sql`).

Do not use LaTeX in your responses. When giving final asnwer, use Markdown.
"""

root_agent = LlmAgent(
    model=custom_model,
    name='data_agent',
    instruction=system_instruction,
    description="A helpful assistant that can answer questions using NYC Citibike data.",
    tools=[bigquery_toolset]
)
