# Copyright 2024 Google LLC.
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

from google import genai
from google.genai import types
from typing import Iterable
import logging
import json
from data_model import ChatMessage, State
import mesop as me

# generation_config = genai.types.GenerateContentConfig()
# generation_config = {
#     "temperature": 1,
#     "top_p": 0.95,
#     "top_k": 64,
#     "max_output_tokens": 8192,
# }

def classify_intent(input: str, history: list[ChatMessage]) -> str:
    state = me.state(State)
    client = genai.Client(api_key=state.gemini_api_key)

    # Combine history and current input to provide full context
    full_history_msgs = history + [ChatMessage(role="user", content=input)]

    # Format for the prompt as seen in the intent_prompt examples
    history_list_of_dicts = [
        {"role": msg.role, "content": msg.content} for msg in full_history_msgs
    ]
    prompt_for_model = f"History: {history_list_of_dicts}"

    json_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_for_model,
        config=types.GenerateContentConfig(
            temperature=1,
            system_instruction=[intent_prompt],
        )
    )
    logging.info(f"INTENT: {json_resp}")
    return json_resp.text.replace("```", "").replace("json", "").strip()

def generate_embedding(input: str) -> list:
    state = me.state(State)
    client = genai.Client(api_key=state.gemini_api_key)
    result = client.models.embed_content(
        model="models/text-embedding-004",
        contents=[input],
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
    )
    return result.embeddings[0].values


def send_prompt_flash(input: str, history: list[ChatMessage],sys_instruction: list[str]) -> Iterable[str]:
    state = me.state(State)
    client = genai.Client(api_key=state.gemini_api_key)

    # Convert history to the format the API expects and add the new user input
    chat_history = [
        {"role": msg.role, "parts": [{"text":msg.content}]} for msg in history
    ]
    chat_history.append({"role": "user", "parts": [{"text":input}]})

    # # Use generate_content with streaming to have a consistent API call style
    response = client.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=chat_history,
        config=types.GenerateContentConfig(
          system_instruction=sys_instruction,
        )
    )

    for chunk in response:
        yield chunk.text

intent_prompt = """
Answer the following questions as a Json string based solely on provided chat history. Do not assume anything that the user did not explicitly say.

	isOnTopic: true or false, indicating whether the most recent query is on topic.
	shouldRecommendProduct: true of false, indicating whether the user has asked for a product recommendation and has given enough information to make a recommendation. If it is a follow up question related to a product or to a previous recommendation then it is true.
	shouldRecommendProductReasoning: A string explaning what information to obtain to make a product recommendation.
	summary: If isOnTopic is true, output a summary of what the user is looking for.
Examples

	History: [{'role': 'user', 'content': "Hi"}]
	Answer: {
 "isOnTopic": true,
 "shouldRecommendProduct": false,
 "shouldRecommendProductReasoning": "User has not mention what they are looking for.",
 "summary": ""
	}

	History: [{'role': 'user', 'content': "Hi, I am looking for a tree for my backyard."}]
	Answer: {
 "isOnTopic": true,
 "shouldRecommendProduct": true,
 "shouldRecommendProductReasoning": "User is looking for a product recommendation.",
 "summary": "A tree to grow on the backyard of a house."
	}"""