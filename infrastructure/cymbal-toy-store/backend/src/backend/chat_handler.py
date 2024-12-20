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

import chat_prompts
import json
import logging
import base64
import httpx
import re

from langchain.prompts import (
	ChatPromptTemplate,
	PromptTemplate,
)
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_google_vertexai import ChatVertexAI
from langchain_google_vertexai import VertexAI
from langchain_google_vertexai import VertexAIEmbeddings
import sqlalchemy
from typing import Any


class ChatHandler():
	def __init__(
		self,
		db: sqlalchemy.engine.base.Engine):
		self.db = db
		self.embeddings_service = VertexAIEmbeddings(
			model_name="textembedding-gecko@003",
		)
		self.chat_llm = ChatVertexAI(
			model_name="gemini-1.5-flash-002",
			max_output_tokens=512,
			temperature=0.0,
			top_p=0.8,
			top_k=20,
			verbose=True,
		)
		self.llm = VertexAI(
			model_name="gemini-1.5-flash-002",
			max_output_tokens=512,
			temperature=0.0,
			top_p=0.8,
			top_k=20,
			verbose=True,
		)


	def _generic_error():
		return "Sorry, something went wrong."


	def _parse_history(self, messages: list[dict[str, str]]) -> list[BaseMessage]:
		prev_prompts = []
		prev_prompts.append(chat_prompts.system_template.format(context=""))
		for prev in messages:
			if prev["role"] == 'user':
				prev_prompts.append(HumanMessage(content=prev['text']))
			elif prev['role'] == 'assistant':
				prev_prompts.append(AIMessage(content=prev['text']))
			elif prev['role'] == 'image':
				prev_prompts.append(HumanMessage(content=prev['image_url']['url']))
		return prev_prompts


	def _classify_intent(self, messages: list[dict[str, str]]) -> str:
		prompt = chat_prompts.intent_template.format(history=f"{messages}")
		json_resp = self.llm.invoke(prompt).replace("```", "").replace("json", "").strip()
		logging.info(f"INTENT: {json_resp}")
		return json_resp


	def _validate_intent_output(self, intent: dict[str, Any]) -> bool:
		for key in ["isOnTopic", "shouldRecommendProduct", "shouldRecommendProductReasoning", "summary"]:
			if key not in intent:
				return False
		return True


	def _gen_system_template(self, context:str) -> SystemMessage:
		added_context=f"Instruction: {context}"		
		template = chat_prompts.system_template.format(context=added_context)
		logging.info(f"SYSTEM: {template.content}")
		print(template)
		return template


	def _find_similar_products(self, text:str, num_matches: int) -> dict[int, dict[str, Any]]:
		ref_embedding = self.embeddings_service.embed_query(text)

		stmt = sqlalchemy.text(
			"""
				SELECT uniq_id, product_name, sale_price, embed_description, product_url
				FROM combined_embedding_products
				ORDER BY embedding <=> :ref_embedding ASC
				LIMIT :num_matches
			"""
		)
		print(stmt)
		with self.db.connect() as conn:
			res = conn.execute(
				stmt,
				parameters={
					"ref_embedding": f"{ref_embedding}",
					"num_matches": num_matches
				}
			)
			matches = {}
			for row in res:
				matches[row[0]] = {"uniq_id": row[0], "name": row[1], "price": float(row[2]), "description": row[3], "image_url": row[4]}
			print(f"Here is the list of products: {matches}")
		return matches
	
	def _extract_url(self,input: str):
    	# Define a regex pattern to match the structure {key: value}
		search_pattern = r"\{[^{}]*?:\s*([^{}]*?)\}"
    	# Search for the first occurrence of the pattern
		match = re.search(search_pattern, input)    
		if match:
        	# Extract the matched piece
			image_url = match.group(1).strip()        
       		 # Remove the matched piece from the original text
			remaining_text = input[:match.start()] + input[match.end():]        
			# Strip extra whitespace (optional)
			remaining_text = remaining_text.strip()        
			return remaining_text, image_url    
		# If no match is found, return the original text and None
		return input, ""


	def _create_response(self, prompts: list[BaseMessage], intent: dict[str, Any],messages: dict[str, Any]) -> dict:
		image_url = ""
		if intent["shouldDescribeImage"]:
			image_prompt = messages[-1]["text"]
			image_data=messages[-1]["image_url"]["url"]
			prompts[0] = HumanMessage(
				content=[
					{"type": "text", "text": f"{image_prompt}"},
					{
						"type": "image_url",
						"image_url": {"url": f"{image_data}"},
					},
				],
			)
			model_response = self.chat_llm.invoke([prompts[0]])
			res_json={}
			res_json['content'] = {'type':'text','text':f'{model_response.content}'}
			res_json['image_url'] = {'type': "image_url", "image_url": {"url": f"{image_data}"}}
			return res_json
		if not intent["isOnTopic"]:
			prompts[0] = self._gen_system_template("Gently redirect the conversation back to toys and other products in the store. Do not use markdown for output")
		elif not intent["shouldRecommendProduct"]:
			prompts[0] = self._gen_system_template(f"Need more information - {intent['shouldRecommendProductReasoning']}")
		else:
			products = self._find_similar_products(intent["summary"], 5)
			print(f"The products: {products}")
			image_url= products[list(products.keys())[0]]["image_url"]
			products_str = "\n".join(str(row) for row in products.values())
			prompts[0] = self._gen_system_template(
				#With RAG
				f"Recommend a suitable product for the user from the below.\n{products_str}\nIn 35 words or less, mention the name (leave out the brand name) and price of the toy, and why the recommended product is a good fit. \nChoose product only from the provided list and suggest only one product from the list.\n Add url for the chosen product to the very end of the responce like: \n {{image_url:https://storage.googleapis.com/gleb-genai-002-cymbal-images-01/1053.jpeg}}\n")
				#Without RAG
				#f"Recommend a suitable product for the user \nIn 35 words or less, mention the name (leave out the brand name) and price of the toy or product, and why the recommended product is a good fit.\n")
		model_response = self.chat_llm.invoke(prompts)
		print(f"Here is model response: {model_response.content}")
		content,image_url = self._extract_url(model_response.content)
		
		print(f"Here is content: {content}")
		print(f"Here is url: {image_url}")
		res_json={}
		res_json['content'] = {'type':'text','text':f'{content}'}
		res_json['image_url'] = {'type': "image_url", "image_url": {"url": f"{image_url}"}}
		print(f"Here is model response: {res_json}")
		return res_json 


	def respond(self, messages: dict[str, Any]) -> str:
		# Parse input
		prompts = self._parse_history(messages)
		# Figure out what to do
		intent_json = self._classify_intent(messages)
		try:
			intent = json.loads(intent_json)
		except json.JSONDecodeError as e:
			logging.exception(f"Failed to decode LLM intent classification as JSON: {intent_json}")
			return self._generic_error()
		if not self._validate_intent_output(intent):
			logging.exception(f"Unexpected LLM output: {intent}")
			return self._generic_error()

		# Create response
		response = self._create_response(prompts, intent, messages)
		logging.info(f"Returning response: {response}")
		return response

