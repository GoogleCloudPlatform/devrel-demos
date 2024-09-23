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
    GEMINI_1_5_FLASH = "Gemini 1.5 Flash"
    OPENAI = "gpt-4o-mini"

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
    openai_api_key: str = ""
    gemma_endpoint_id: str = ""
    location: str = ""
    in_progress: bool = False

@me.stateclass
class ModelDialogState:
    selected_models: list[str] = field(default_factory=list)