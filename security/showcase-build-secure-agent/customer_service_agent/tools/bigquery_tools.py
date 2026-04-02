# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import google.auth
from google.auth.transport.requests import Request

# BigQuery MCP toolset imports
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode


# =============================================================================
# Configuration
# =============================================================================

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")


def get_bigquery_mcp_toolset() -> BigQueryToolset:
    """
    Create an McpToolset connected to Google's managed BigQuery MCP server.
    """
    tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)
    application_default_credentials, _ = google.auth.default()
    credentials_config = BigQueryCredentialsConfig(
        credentials=application_default_credentials
    )

    bigquery_toolset = BigQueryToolset(
        credentials_config=credentials_config, bigquery_tool_config=tool_config
    )

    print(f"[BigQueryTools] configured to work for project: {PROJECT_ID}")

    return bigquery_toolset


def get_customer_service_instructions() -> str:
    """
    Get additional instructions for the agent about BigQuery access.
    """
    return f"""
## BigQuery Data Access

You have access to customer service data via BigQuery MCP tools.

**Project ID:** {PROJECT_ID}
**Dataset:** customer_service

**Available Tables:**
- `customer_service.customers` - Customer information
- `customer_service.orders` - Order history  
- `customer_service.products` - Product catalog

**Available MCP Tools:**
- `list_table_ids` - Discover what tables exist in a dataset
- `get_table_info` - Get table schema (column names and types)
- `execute_sql` - Run SELECT queries

**IMPORTANT:** Before writing any SQL query, use `get_table_info` to discover 
the exact column names for the table you want to query. Do not guess column names.

**Access Restrictions:**
You only have access to the `customer_service` dataset. You do NOT have access 
to administrative tables like `admin.audit_log`. If a customer asks about admin 
data, politely explain that you only have access to customer service data.
"""


if __name__ == "__main__":
    print("Testing BigQuery MCP connection...")

    try:
        toolset = get_bigquery_mcp_toolset()
        print("✅ BigQuery MCP toolset created successfully!")
        print(f"   Tools available: {toolset}")
    except Exception as e:
        print(f"❌ Error: {e}")
