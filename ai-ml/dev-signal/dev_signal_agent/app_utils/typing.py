import uuid
from typing import Literal
from pydantic import BaseModel, Field

class Feedback(BaseModel):
    """Represents feedback for a conversation."""
    score: int | float
    text: str | None = ""
    log_type: Literal["feedback"] = "feedback"
    service_name: str = "dev_signal_agent"
    # Auto-generate IDs if not provided
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

