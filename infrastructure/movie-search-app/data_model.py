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

import mesop as me
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

Role = Literal["user", "model"]

# Data Model
@dataclass(kw_only=True)
class ChatMessage:
    role: Role = "user"
    content: str = ""
    in_progress: bool = False

class Models(Enum):
    GEMINI_1_5_FLASH = "PostgreSQL"
    PINECONE = "Pinecone"

@dataclass
class Conversation:
    model: str = ""
    messages: list[ChatMessage] = field(default_factory=list)

@me.stateclass
class State:
    is_model_picker_dialog_open: bool = False
    input: str = ""
    conversations: list[Conversation] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    gemini_api_key: str = ""
    pinecone_api_key: str = ""
    location: str = ""
    in_progress: bool = False

@me.stateclass
class ModelDialogState:
    selected_models: list[str] = field(default_factory=list)