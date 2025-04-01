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

#import anthropic
from openai import OpenAI
from typing import Iterable
import logging
import requests

from data_model import ChatMessage, State
import mesop as me

def classify_intent(input: str) -> str:
    state = me.state(State)
    print(state.gemma_endpoint_id)
    client= OpenAI(api_key="EMPTY",base_url=state.gemma_endpoint_id)
    completion = client.chat.completions.create(
        model="google/gemma-3-4b-it",
        messages=[
            {"role": "system", "content": intent_prompt},
            {"role": "user", "content": input}
        ]
    )
    json_resp = completion.choices[0].message.content
    logging.info(f"INTENT: {json_resp}")
    return json_resp.replace("```", "").replace("json", "").strip()

def generate_embedding(input: str) -> list[float]:
    state = me.state(State)
    tei_url=state.tei_embedding_url
    HEADERS = {
    "Content-Type": "application/json"
    }
    payload = {
            "inputs": input,
            "truncate": True
        }
    print(payload)
    resp = requests.post(tei_url, json=payload, headers=HEADERS)
    if resp.status_code != 200:
        raise RuntimeError(resp.text)
    result = resp.json()[0]
    #print(result)
    return result


def call_gemma(input: str, history: list[ChatMessage],sys_instruction: str) -> Iterable[str]:
    state = me.state(State)
    client = OpenAI(api_key="EMPTY",base_url=state.gemma_endpoint_id)
    models = client.models.list()
    model = models.data[0].id
    print(model)
    chat_messages = [
        {
            "role": "assistant" if message.role == "model" else message.role,
            "content": message.content,
        }
        for message in history
    ] + [{"role": "user", "content": input}, {"role": "system", "content": sys_instruction}]

    with client.chat.completions.create(
    model=model,
    messages=chat_messages,
    temperature=0,
    stream=True  # again, we set stream=True
    ) as stream:
        for part in stream:
            yield part.choices[0].delta.content

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