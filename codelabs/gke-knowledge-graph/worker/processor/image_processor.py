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
import json
from google import genai
from google.genai import types

def process_image(gcs_path: str):
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_REGION", "US")
    client = genai.Client(vertexai=True, project=project, location=location)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = """
    Analyze this image. Extract entities related to pets (pets, objects, actions) and create nodes and edges between them.
    Extract the pet, breed, and if they exist: toys, food, actions (play, sleep, eat) as hobbies.
    Respond strictly in JSON with two keys top build a graph: 'nodes' and 'edges'.
    Nodes MUST include: 'entity_id', 'entity_type', 'properties' (JSON).
    Edges MUST include: 'source_id', 'target_id', 'relationship', 'properties' (JSON).
    """

    # Determining mime_type based on simple heuristics for the lab
    mime_type = "image/png" if gcs_path.endswith(".png") else "image/jpeg"

    file_part = types.Part.from_uri(
        file_uri=gcs_path,
        mime_type=mime_type
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[prompt, file_part]
    )

    try:
        # Simple cleaning of markdown code fences if any
        cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
        result = json.loads(cleaned_text)
        return result.get('nodes', []), result.get('edges', [])
    except Exception:
        return [], []
