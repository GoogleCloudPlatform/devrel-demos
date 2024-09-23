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
from cymbal_store import ChatMessage, State
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
    #json_resp = self.llm(prompt).replace("```", "")
    #print(json_resp.text)
    logging.info(f"INTENT: {json_resp}")
    return json_resp.text

def generate_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model="models/text-embedding-004",
        content="What is the meaning of life?",
        task_type="retrieval_document",
        title="Embedding of single string")
    return result


def send_prompt_flash(input: str, history: list[ChatMessage],sys_instruction: list[str]) -> Iterable[str]:
    # intent_str = classify_intent(input)
    # try:
    #     json_intent = json.loads(intent_str)
    # except json.JSONDecodeError as e:
    #     print(f"Error decoding JSON: {e}")
    # json_intent = json.loads(intent_str)
    # if json_intent["shouldRecommendProduct"] is True:
    #     print("we need embeddings")
    #     search_embedding = generate_embedding(json_intent["summary"])
    #     persona="You are friendly assistance in a store helping to find a products based on the client's request"
    #     safeguards="You should give information about the product, price and any supplemental information. Do not invent any new products and use for the answer the product defined in the context"
    #     context=""
    #     system_instruction=[persona,safeguards]
    # else:
    #     persona="You are friendly assistance in a store helping to find a products based on the client's request"
    #     safeguards="You should give information about the product, price and any supplemental information. Do not invent any new products and use for the answer the product defined in the context"
    #     system_instruction=[persona,safeguards]
    configure_gemini()
    # print(search_embedding)
    # system_instructions = {
    #     "persona":"You are friendly assistance in a store helping to find a products based on the client's request",
    #     "context":"The list in JSON format with list of values like {'product_name':'some name','product_description':'some description','sale_price':10} Here is the list of products: ",
    #     "safeguard":"You should give information about the product, price and any supplemental information. Do not invent any new products and use for the answer the product defined in the context",
    # }
    # for prompt in system_instructions:
    #     if prompt["prompt_part"] == "persona":
    #         persona = prompt["prompt"]
    #     elif prompt["prompt_part"] == "safeguards":
    #         safeguards = prompt["prompt"]
    #     elif prompt["prompt_part"] == "context":
    #         context = prompt["prompt"]
    # system_instruction=[persona,safeguards]
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