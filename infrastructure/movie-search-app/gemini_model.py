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

import google.generativeai as genai
from typing import Iterable
import logging
import json
from data_model import ChatMessage, State
import mesop as me

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

def configure_gemini():
    state = me.state(State)
    genai.configure(api_key=state.gemini_api_key)

def classify_intent(input: str) -> str:
    configure_gemini()
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=generation_config,
        system_instruction=[intent_prompt],
    )
    json_resp = model.generate_content(input)
    logging.info(f"INTENT: {json_resp}")
    return json_resp.text

def generate_embedding(input: str) -> list[float]:
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=input,
        task_type="retrieval_document",
        title="Embedding of single string")
    return result


def send_prompt_flash(input: str, history: list[ChatMessage],sys_instruction: list[str]) -> Iterable[str]:
    configure_gemini()
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=generation_config,
        system_instruction=sys_instruction,
    )
    chat_session = model.start_chat(
        history=[
            {"role": message.role, "parts": [message.content]} for message in history
        ]
    )
    for chunk in chat_session.send_message(input, stream=True):
        yield chunk.text

intent_prompt = """
Answer the following questions as a Json string based solely on provided chat history. Do not assume anything that the user did not explicitly say.

	isOnTopic: true or false, indicating whether the most recent query is on topic.
	shouldRecommendMovie: true of false, indicating whether the user has asked for a movie or show recommendation and has given enough information to make a recommendation. If it is a follow up question related to a product or to a previous recommendation then it is true.
	shouldRecommendMovieReasoning: A string explaning what information to obtain to make a movie or show recommendation.
	summary: If isOnTopic is true, output a summary of what the user is looking for.
Examples

	History: [{'role': 'user', 'content': "Hi"}]
	Answer: {
 "isOnTopic": true,
 "shouldRecommendMovie": false,
 "shouldRecommendMovieReasoning": "User has not mention what they are looking for.",
 "summary": ""
	}

	History: [{'role': 'user', 'content': "Hi, I am looking for a movie about a spy changing faces."}]
	Answer: {
 "isOnTopic": true,
 "shouldRecommendMovie": true,
 "shouldRecommendMovieReasoning": "User is looking for a movie recommendation.",
 "summary": "A movie about a spy changing faces."
	}
    Do not use markdown for the output, respond with only JSON 
    """