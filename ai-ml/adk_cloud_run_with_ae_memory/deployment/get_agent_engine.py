# Copyright 2025 Google LLC
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
"""Agent Engine Registration Tool."""

import argparse

from vertexai import init
from vertexai.agent_engines import create, list as list_engines


def get_agent_engine(
        agent_name: str,
        project_id: str,
        location: str
    ) -> str:
    """Creates an Agent Engine or retrieves an existing one based in its display name.

    Args:
        agent_name (str): Display name of the Agent Engine instance to create.
        project_id (str): Project Id.
        location (str): Location to create the Agent Engine in.


    Returns:
        str: Agent Engine Id
    """

    init(
        project=project_id,
        location=location,
    )
    agents = list(
        list_engines(
            filter=f'display_name="{agent_name}"'
        )
    )
    if agents:
        return agents[0].resource_name
    else:
        return create(
            display_name=agent_name
        ).resource_name


################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Agent Engine Creator"
    )
    parser.add_argument(
        "--agent-name",
        "-n",
        required=True,
        type=str,
        help="Name of the Agent Engine instance to create."
    )
    parser.add_argument(
        "--project-id",
        "-p",
        required=True,
        type=str,
        help="Id of a Google Cloud Project to create the Agent Engine in.",
    )
    parser.add_argument(
        "--location",
        "-l",
        required=True,
        type=str,
        help="Google Cloud region to create the Agent Engine in.",
    )
    args = parser.parse_args()
    agent_id = get_agent_engine(
        agent_name=args.agent_name,
        project_id=args.project_id,
        location=args.location,
    )
    if agent_id:
        agent_id = agent_id.rsplit("/", 1)[-1]
        print(agent_id)
