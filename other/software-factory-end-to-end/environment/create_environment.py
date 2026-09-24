#!/usr/bin/env python3
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

"""Persistent Sandbox Environment Provisioner.

Initializes an interaction with `antigravity-preview-05-2026` using config object
`environment={"type": "remote"}` on Vertex AI (location="global").
Captures the canonical server-assigned `environment_id` (`env_CAEQ...`),
displays it clearly to stdout in a banner, and appends it to `.env` as `ANTIGRAVITY_ENV_ID`.
"""

import os
import sys
from google import genai
import google.auth


def provision_sandbox() -> str | None:
    # Resolve project from ADC or environment
    _, default_project = google.auth.default()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or default_project
    location = os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"
    agent_id = "antigravity-preview-05-2026"

    print(f"Initializing Vertex AI GenAI Client (project={project_id}, location={location})...")
    client = genai.Client(vertexai=True, project=project_id, location=location)

    print(f"Creating interaction with agent='{agent_id}' and environment={{'type': 'remote'}}...")
    try:
        stream = client.interactions.create(
            agent=agent_id,
            input="echo 'initializing sandbox'",
            extra_body={"environment": {"type": "remote"}},
            stream=True,
            background=True,
            store=True,
            timeout=120,
        )

        interaction_id = None
        environment_id = None

        for event in stream:
            if hasattr(event, "interaction") and event.interaction:
                interaction_id = getattr(event.interaction, "id", interaction_id)

            if event.event_type == "interaction.created":
                print(f"[Created] Interaction ID: {interaction_id}")
            elif event.event_type == "interaction.completed":
                inter = getattr(event, "interaction", None)
                environment_id = getattr(inter, "environment_id", None)
                print(f"[Completed] Interaction ID: {interaction_id}")

        # Fallback query if not populated on stream completion event
        if not environment_id and interaction_id:
            inter = client.interactions.get(interaction_id)
            environment_id = getattr(inter, "environment_id", None)

        if not environment_id:
            print("Error: Could not retrieve environment_id from interaction.", file=sys.stderr)
            return None

        # Print banner
        print("\n" + "=" * 80)
        print(" PERSISTENT SANDBOX PROVISIONED SUCCESSFULLY")
        print(f" Environment ID: {environment_id}")
        print("=" * 80)

        # Save to local .env file
        env_file = os.path.join(os.getcwd(), ".env")
        with open(env_file, "a") as f:
            f.write(f"ANTIGRAVITY_ENV_ID={environment_id}\n")
        print(f"Saved to: .env (ANTIGRAVITY_ENV_ID={environment_id})\n")

        return environment_id

    except Exception as e:
        print(f"\nAPI Error during sandbox provisioning: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    env_id = provision_sandbox()
    if not env_id:
        sys.exit(1)
