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

import os
import uuid
import requests
import json

def get_agent_response(user_id, session_id, blog_post_markdown, feedback):
    agent_url = os.getenv('AGENT_URL')
    if not agent_url:
        return ("", "", "")
    if not user_id:
        (user_id, session_id) = create_session()
    prompt = (
        f'Apply this feedback: "{feedback}" to this blog post: '
        f'"{blog_post_markdown}"'
    )
    url = f"{agent_url}/run_sse"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_name": "blog_refiner",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{
                "text": prompt
            }]
        },
        "streaming": False
    }
    response = requests.post(url, headers=headers, json=data)
    sse_messages = response.text.strip().split("data: ")
    last_message = sse_messages[-1]
    data = json.loads(last_message)
    refined_text = data['content']['parts'][0]['text']
    return (user_id, session_id, refined_text)

def create_session():
    agent_url = os.getenv('AGENT_URL')
    if not agent_url:
        raise ValueError("Set the environment variable AGENT_URL")
    new_uuid = str(uuid.uuid4())
    session_id = f"session-{new_uuid}"
    user_id = f"user-{new_uuid}"
    url = f"{agent_url}/apps/blog_refiner/users/{user_id}/sessions/{session_id}"
    headers = {"Content-Type": "application/json"}
    data = {"state": {"preferred_language": "English", "visit_count": 5}}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise ValueError(f"Failed to create session: {response.text}")
    return (user_id, session_id)
