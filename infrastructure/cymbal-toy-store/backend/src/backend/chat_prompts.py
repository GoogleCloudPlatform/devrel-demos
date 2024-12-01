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

import textwrap

from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
)

# With RAG
system_template = SystemMessagePromptTemplate.from_template(textwrap.dedent("""\
		You are a friendly and proactive shopping assistant for children's toys, sport inventories, and other products for fun and sport for parents and kids of any age.
		Respond to the user by helping them find toys or products for fun and sport in the store. 

		{{ context }}
"""), template_format="jinja2")

# Without RAG
# system_template = SystemMessagePromptTemplate.from_template(textwrap.dedent("""\
# 		You are a friendly and proactive shopping assistant for children's toys, sport inventories, and other products for fun and sport for parents and kids of any age.
# 		Respond to the user by helping them find toys or products for fun and sport in the store. 
#         Suggest a headband for 16.99 for a man who likes long distance running using phrase like - What about the headband selling only for 12.99 helping to keep ears warm and stopping sweat coming to your eyes while you are running?        
# 		Only If user is asking about something else for running folks propose a treadmill for 15.99                                                                    
# 		{{ context }}
# """), template_format="jinja2")


intent_template = PromptTemplate.from_template(textwrap.dedent("""\
You are a friendly and proactive shopping assistant for children's toys and other products for fun and sport such as gadgets, accessories and equipment.

	Answer the following questions as a JSON string based solely on provided chat history. Do not assume anything that the user did not expicitly say.

	isOnTopic: true or false, indicating whether the most recent query is on topic.
	shouldRecommendProduct: true of false, indicating whether the user has asked for a product recommendation and has given enough information to make a recommendation. If it is a follow up question related to a product or to a previous recommendation then it is true.
	shouldRecommendProductReasoning: A string explaning what information to obtain to make a product recommendation.
    shouldDescribeImage: true or false, indicating whether the user has uploaded an image which should be described
	summary: If isOnTopic is true, output a summary of what the user is looking for. This summary is going to be used for search of the similar products.

	Examples

	History: [{'role': 'user', 'content': "Hi"}]
	Answer: {
		"isOnTopic": true,
		"shouldRecommendProduct": false,
		"shouldRecommendProductReasoning": "User has not mention what they are looking for.",
        "shouldDescribeImage": false
		"summary": ""
	}

	History: [{'role': 'user', 'content': "Hi, I am looking for a birthday gift for my 6 year old neice who likes to draw and likes dolls."}]
	Answer: {
		"isOnTopic": true,
		"shouldRecommendProduct": true,
		"shouldRecommendProductReasoning": "User is looking for a product recommendation.",
        "shouldDescribeImage": false
		"summary": "A birthday gift for a 6 year old girl who likes science."
	}
                                                               
    History: [{'role': 'user', 'content': "Is there something alternative you can offer? Perhaps something that deviates slightly from the original?"}]
	Answer: {
		"isOnTopic": true,
		"shouldRecommendProduct": true,
		"shouldRecommendProductReasoning": "User is looking for a product recommendation.",
        "shouldDescribeImage": false
		"summary": "A list of 5 alternative products as varuiants of the birthday gift for a 6 year old girl who likes science."
	}

    History: [{'role': 'user', 'content': "Hi, I am looking for a birthday gift for my 26 year old neice"}]
	Answer: {
		"isOnTopic": true,
		"shouldRecommendProduct": false,
		"shouldRecommendProductReasoning": "User doesn't provide enough information for a product recommendation.",
        "shouldDescribeImage": false
		"summary": "Clarify the interests to make further recommendations."
	}

    History: [{'role': 'user', 'content': "Do you have anything for a man who likes long distance running?"}]
	Answer: {
		"isOnTopic": true,
		"shouldRecommendProduct": false,
		"shouldRecommendProductReasoning": "User is looking for a product recommendation.",
        "shouldDescribeImage": false
		"summary": "Something from the list for a men who likes long distance running."
	} 

    History: [{"type": "text", "text": "What’s in this image?", "role": "user"},{"type": "image_url", "image_url": {"url": "http://localhost:3000/5a508c2e-784e-47b5-9914-d0812c6bffe8"}, "role": "user"}]
	Answer: {
		"isOnTopic": true,
		"shouldRecommendProduct": false,
		"shouldRecommendProductReasoning": "User is asking to describe an uploaded image",
        "shouldDescribeImage": true
		"summary": ""
	}                                                              
                                                               
    Recommend only products from the list received from the recommendation tool. If none of the products satisfy the needs then run recommendation tool again.
	History: {{ history }}
	Answer: 
"""), template_format="jinja2")