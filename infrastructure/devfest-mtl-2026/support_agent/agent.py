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

"""DevFest Montréal 2026: Google ADK Agent + Skills + Dual AlloyDB MCP Modes.

Supports two MCP architectures toggled via `MCP_MODE`:
  1. `MCP_MODE=toolbox` (default): Connects to MCP Toolbox for Databases
     (`http://127.0.0.1:5000` locally, or `TOOLBOX_URL` with Workload Identity on Cloud Run).
  2. `MCP_MODE=remote`: Connects directly to the managed Google Cloud AlloyDB Remote MCP
     endpoint (`https://alloydb.googleapis.com/mcp` or regional endpoint) over Streamable HTTP.
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

import google.auth
import google.auth.exceptions
from google.auth.transport.requests import Request
from google.adk.agents import LlmAgent
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset


SKILL_DIR = pathlib.Path(__file__).parent / "skills" / "ticket-triage"


def build_database_toolset():
    """Return either ToolboxToolset (Option 1) or Remote McpToolset (Option 2)."""
    mcp_mode = os.getenv("MCP_MODE", "toolbox").strip().lower()

    if mcp_mode == "remote":
        from google.adk.tools.mcp_tool import McpToolset
        from google.adk.tools.mcp_tool.mcp_session_manager import (
            StreamableHTTPConnectionParams,
        )

        endpoint = os.getenv("ALLOYDB_MCP_URL", "https://alloydb.googleapis.com/mcp")
        read_only = os.getenv("MCP_READ_ONLY", "false").lower() == "true"
        allowed_tools = [
            "list_clusters",
            "list_instances",
            "get_instance",
            "execute_sql_read_only",
        ]
        if not read_only:
            allowed_tools.append("execute_sql")

        cached_creds: dict[str, Any] = {"credentials": None}

        def get_remote_mcp_headers(_context: Any = None) -> dict[str, str]:
            """Dynamically provide a valid OAuth bearer token on every MCP request."""
            token = os.getenv("GCP_OAUTH_TOKEN")
            if not token:
                creds = cached_creds["credentials"]
                if creds is None:
                    creds, _ = google.auth.default(
                        scopes=["https://www.googleapis.com/auth/cloud-platform"]
                    )
                    cached_creds["credentials"] = creds
                if not creds.valid:
                    creds.refresh(Request())
                token = creds.token

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            quota_project = os.getenv("ALLOYDB_PROJECT_ID") or os.getenv(
                "GOOGLE_CLOUD_PROJECT"
            )
            if quota_project:
                headers["X-Goog-User-Project"] = quota_project
            return headers

        base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        try:
            base_headers = get_remote_mcp_headers()
        except google.auth.exceptions.GoogleAuthError:
            pass

        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=endpoint,
                headers=base_headers,
            ),
            header_provider=get_remote_mcp_headers,
            tool_filter=allowed_tools,
        )

    # Option 1 (default): MCP Toolbox for Databases (local binary or Cloud Run service)
    from google.adk.tools.toolbox_toolset import ToolboxToolset

    toolbox_url = os.getenv("TOOLBOX_URL", "http://127.0.0.1:5000")
    toolset_name = os.getenv("TOOLBOX_TOOLSET", "support_triage_toolset")

    if os.getenv("K_SERVICE") and toolbox_url.startswith("https://"):
        from toolbox_adk import CredentialStrategy

        creds = CredentialStrategy.workload_identity(target_audience=toolbox_url)
        return ToolboxToolset(
            server_url=toolbox_url,
            toolset_name=toolset_name,
            credentials=creds,
        )

    return ToolboxToolset(
        server_url=toolbox_url,
        toolset_name=toolset_name,
    )


def create_support_agent() -> LlmAgent:
    """Instantiate the grounded ADK LlmAgent with SkillToolset + AlloyDB MCP tools."""
    triage_skill = load_skill_from_dir(SKILL_DIR)
    skill_tools = SkillToolset(skills=[triage_skill])
    db_tools = build_database_toolset()

    mcp_mode = os.getenv("MCP_MODE", "toolbox").strip().lower()
    alloydb_ctx = (
        f"Default AlloyDB context when calling remote MCP tools: "
        f"project='{os.getenv('ALLOYDB_PROJECT_ID', 'devfest-project')}', "
        f"location='{os.getenv('ALLOYDB_REGION', 'us-west1')}', "
        f"cluster='{os.getenv('ALLOYDB_CLUSTER', 'devfest-cluster')}', "
        f"instance='{os.getenv('ALLOYDB_INSTANCE', 'devfest-cluster-pr')}', "
        f"database='{os.getenv('ALLOYDB_DATABASE', 'support_db')}', "
        f"user='{os.getenv('ALLOYDB_IAM_USER', 'postgres')}'."
    )

    return LlmAgent(
        model=os.getenv("ADK_MODEL", "gemini-2.5-flash"),
        name="support_data_agent",
        description="Montréal TechGear customer support & order triage agent grounded in AlloyDB.",
        instruction=(
            "You are the Montréal TechGear Support & Order Triage Agent.\n"
            "1. Always load and follow the `ticket-triage` skill before triaging tickets, "
            "evaluating SLAs, or recommending credits.\n"
            "2. Ground every answer strictly in live AlloyDB records via your MCP tools — "
            "never invent ticket IDs, order amounts, or customer tiers.\n"
            f"3. Active MCP architecture mode: `{mcp_mode}`. {alloydb_ctx}"
        ),
        tools=[skill_tools, db_tools],
    )


root_agent = create_support_agent()
