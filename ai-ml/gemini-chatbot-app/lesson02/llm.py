#!/usr/bin/env python
#
# Copyright 2024 Google, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import openai
import vertexai

from google.auth import default, transport


# TODO(Developer): Update project name
MODEL_NAME = "google/gemini-1.5-flash-001"
PROJECT_ID = "cloud-devrel-tools"
LOCATION = "us-central1"


def get_chat_client(project_id, location):
    # Initialize vertexai
    vertexai.init(project=project_id, location=location)

    # Programmatically get an access token
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_request = transport.requests.Request()
    credentials.refresh(auth_request)

    # OpenAI client for Gemini-Flash-1.5
    client = openai.OpenAI(
        base_url=f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/endpoints/openapi",
        api_key=credentials.token,
    )
    return client


def get_response(gemini_client, prompt="Why is the sky blue?"):
    response = gemini_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return response.choices[0].message.content
    except:
        return response


def main():
    return get_chat_client(PROJECT_ID, LOCATION)
