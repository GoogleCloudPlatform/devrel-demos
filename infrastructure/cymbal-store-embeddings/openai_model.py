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

from data_model import ChatMessage, State
import mesop as me

def call_openai_gpt4o_mini(input: str, history: list[ChatMessage]) -> Iterable[str]:
    state = me.state(State)
    client = OpenAI()
    #client = anthropic.Anthropic(api_key=state.claude_api_key)
    messages = [
        {
            "role": "assistant" if message.role == "model" else message.role,
            "content": message.content,
        }
        for message in history
    ] + [{"role": "user", "content": input}]

    with client.messages.stream(
        max_tokens=1024,
        messages=messages,
        model="gpt-4o-mini",
    ) as stream:
        for text in stream.text_stream:
            yield text