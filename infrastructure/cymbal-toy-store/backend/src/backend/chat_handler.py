import chat_prompts
import json
import logging

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
			max_output_tokens=512,
			temperature=0.0,
			top_p=0.8,
			top_k=20,
			verbose=True,
		)
		self.llm = VertexAI(
			model_name="gemini-1.0-pro-001",
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
		return prev_prompts


	def _classify_intent(self, messages: list[dict[str, str]]) -> str:
		prompt = chat_prompts.intent_template.format(history=f"{messages}")
		json_resp = self.llm(prompt).replace("```", "")
		logging.info(f"INTENT: {json_resp}")
		return json_resp


	def _validate_intent_output(self, intent: dict[str, Any]) -> bool:
		for key in ["isOnTopic", "shouldRecommendProduct", "shouldRecommendProductReasoning", "summary"]:
			if key not in intent:
				return False
		# We should also check type here
		return True


	def _gen_system_template(self, context:str) -> SystemMessage:
		added_context=f"Instruction: {context}"		
		template = chat_prompts.system_template.format(context=added_context)
		logging.info(f"SYSTEM: {template.content}")
		return template


	def _find_similar_products(self, text:str, num_matches: int) -> dict[int, dict[str, Any]]:
		ref_embedding = self.embeddings_service.embed_query(text)

		stmt = sqlalchemy.text(
			"""
				SELECT uniq_id, product_name, sale_price, embed_description
				FROM combined_embedding_products
				ORDER BY embedding <=> :ref_embedding ASC
				LIMIT :num_matches
			"""
		)
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
				matches[row[0]] = {"name": row[1], "price": float(row[2]), "description": row[3]}
		return matches


	def _create_response(self, prompts: list[BaseMessage], intent: dict[str, Any]) -> str:
		if not intent["isOnTopic"]:
			prompts[0] = self._gen_system_template("Gently redirect the conversation back to toys.")
		elif not intent["shouldRecommendProduct"]:
			prompts[0] = self._gen_system_template(f"Need more information - {intent['shouldRecommendProductReasoning']}")
		else:
			products = self._find_similar_products(prompts[-1].content, 5)
			products_str = "\n".join(str(row) for row in products.values())
			prompts[0] = self._gen_system_template(
				f"Recommend a suitable product for the user from the below.\n{products_str}\nIn 35 words or less, mention the name (leave out the brand name) and price of the toy, and why the recommended product is a good fit.Choose product only from the provided list.\n")
		return self.chat_llm(prompts).content		


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
		response = self._create_response(prompts, intent)
		logging.info(f"Returning response: {response}")
		return response



