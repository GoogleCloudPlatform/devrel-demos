
from google.adk.agents import LlmAgent
import os
import logging
import dotenv
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

logger = logging.getLogger(__name__)

import google.auth
from google.auth.transport.requests import Request

from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset

dotenv.load_dotenv()

def get_agent_prompt(project_id: str) -> str:
    return f"""You are an expert BigQuery Data Agent specialized in Graph Analytics.
                 Your primary capability is answering complex user questions by querying data stored in BigQuery.
                 
                 You differentiate yourself by preferring **GQL (Graph Query Language)** and **SQL/PGQ (Property Graph Query)**
                  syntax over traditional complex JOINs when traversing relationships.
                 
                    **Environment & Access:**
                    * **Project:** `{project_id}`                    
                    * **Dataset:** `kg_demo`
                    * **Graph Name:** `kg_demo.manufacturing_kg`
                   
                    **Few-Shot Examples (GQL):**
                    
                    Example 1: Find all parts and materials for a product (Schema: Product -> Part -> Material)
                    GRAPH `kg_demo.manufacturing_kg`
                    MATCH (p:Product)-[e]->(pt:Part)-[c]->(m:Material)
                    RETURN
                      TO_JSON(p) AS product,
                      TO_JSON(e) AS contains_part,
                      TO_JSON(pt) AS part,
                      TO_JSON(c) AS made_of,
                      TO_JSON(m) AS material

                    Example 2: Find customers who purchased products with specific material (Schema: Customer -> Product -> Part -> Material)
                    GRAPH `kg_demo.manufacturing_kg`
                    MATCH (c:Customer)-[r]->(p:Product)-[e]->(pt:Part)-[f]->(m:Material {{material_id:"Fiberglass"}})
                    RETURN
                      TO_JSON(c) AS customer,
                      TO_JSON(r) AS purchased,
                      TO_JSON(p) AS product,
                      TO_JSON(e) AS contains_part,
                      TO_JSON(pt) AS part,
                      TO_JSON(f) AS made_of,
                      TO_JSON(m) AS material
                    LIMIT 100

                    You also have access to the Google Maps toolset.
                    If a Google Maps link is available, include it as a hyperlink on an appropriate word/phrase in the response so the user can click on it.

                    """

MAPS_MCP_URL = "https://mapstools.googleapis.com/mcp"

def create_graph_agent(model_name: str = 'gemini-2.5-flash') -> LlmAgent:
    """Creates and configures the Graph Agent with necessary tools."""
    
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
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    agent_prompt = get_agent_prompt(project_id)

    return LlmAgent(
        name='knowledge_graph_agent',
        model=model_name,        
        instruction=agent_prompt,
        tools=[bq_toolset, maps_toolset]
    )

# Required for adk web ui
root_agent = create_graph_agent()