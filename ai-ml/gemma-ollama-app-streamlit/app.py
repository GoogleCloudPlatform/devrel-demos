#!/usr/bin/env python
#
# Copyright 2024 Google, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from typing import Type, Tuple
import json
import streamlit as st

GEMMA_MODEL = "gemma2:9b"


class Settings(BaseSettings):
    ollama_cloudrun_service_account: str
    ollama_cloudrun_service_url: str

    model_config = SettingsConfigDict(
        yaml_file="settings.yaml", yaml_file_encoding="utf-8"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls),)


settings = Settings()

url = f"{settings.ollama_cloudrun_service_url}/api/chat"
creds = service_account.IDTokenCredentials.from_service_account_file(
    settings.ollama_cloudrun_service_account, target_audience=url
)

authed_session = AuthorizedSession(creds)

st.title("Ollama Gemma Bot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def stream_response(chat_messages: list[dict]):
    data = {"model": GEMMA_MODEL, "messages": chat_messages}
    with authed_session.post(url, json=data, stream=True) as response:
        for line in response.iter_lines():
            response = json.loads(line.decode("utf-8"))

            yield response["message"]["content"]


# React to user input
if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        response = st.write_stream(stream_response(st.session_state.messages))

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
