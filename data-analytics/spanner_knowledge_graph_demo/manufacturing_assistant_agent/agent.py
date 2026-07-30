# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import LlmAgent
import os
import logging
import dotenv
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
import google.auth
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

def get_agent_prompt(project_id: str) -> str:
    return f"""You are an expert BigQuery & Cloud Spanner Data Agent specialized in Hybrid Graph Analytics & Reverse ETL.
Your primary capability is answering complex customer and engineering questions by traversing knowledge graphs stored in BigQuery and Cloud Spanner.

You differentiate yourself by preferring **GQL (Graph Query Language)** and **SQL/PGQ (Property Graph Query)**
syntax over traditional complex JOINs when traversing relationships.

**Environment & Access:**
* **Project:** `{project_id}`
* **Dataset:** `kg_demo`
* **BigQuery Property Graph:** `kg_demo.manufacturing_kg`
* **Spanner Graph:** `spanner_manufacturing_graph`

**Few-Shot Examples (BigQuery GQL):**

Example 1: Find all parts and materials for a product (Schema: Product -> Part -> Material)
GRAPH `kg_demo.manufacturing_kg`
MATCH (p:Product)-[e:CONTAINS_PART]->(pt:Part)-[c:IS_MADE_OF]->(m:Material)
RETURN
  TO_JSON(p) AS product,
  TO_JSON(e) AS contains_part,
  TO_JSON(pt) AS part,
  TO_JSON(c) AS made_of,
  TO_JSON(m) AS material

Example 2: Find customer complaints and trace root-cause materials (Schema: Customer -> Complaint -> Product -> Part -> Material)
GRAPH `kg_demo.manufacturing_kg`
MATCH (c:Customer)-[comp:HAS_COMPLAINT]->(p:Product)-[e:CONTAINS_PART]->(pt:Part)-[f:IS_MADE_OF]->(m:Material)
RETURN
  TO_JSON(c) AS customer,
  TO_JSON(comp) AS complaint,
  TO_JSON(p) AS product,
  TO_JSON(pt) AS part,
  TO_JSON(m) AS material
LIMIT 100

You also have access to the Google Maps toolset.
If a Google Maps link is available, include it as a hyperlink on an appropriate word/phrase in the response so the user can click on it.
"""

MAPS_MCP_URL = "https://mapstools.googleapis.com/mcp"

def create_graph_agent(model_name: str = 'gemini-2.5-flash') -> LlmAgent:
    """Creates and configures the Graph Agent with necessary toolsets."""
    
    # 1. Setup Maps Toolset
    maps_api_key = os.getenv('MAPS_API_KEY')
    if not maps_api_key:
        logger.warning("MAPS_API_KEY not found in environment.")

    maps_toolset = MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MAPS_MCP_URL,
            headers={"X-Goog-Api-Key": maps_api_key},
        ), 
        errlog=None
    )

    # 2. Setup BigQuery Toolset    
    credentials, _ = google.auth.default()
    bq_toolset = BigQueryToolset(
        credentials_config=BigQueryCredentialsConfig(credentials=credentials), 
        tool_filter=['list_table_ids', 'get_table_info', 'execute_sql', 'get_dataset_info'] 
    )

    # 3. Create Agent
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
    agent_prompt = get_agent_prompt(project_id)

    return LlmAgent(
        name='spanner_kg_agent',
        model=model_name,        
        instruction=agent_prompt,
        tools=[bq_toolset, maps_toolset]
    )

# Required for adk web ui
root_agent = create_graph_agent()
