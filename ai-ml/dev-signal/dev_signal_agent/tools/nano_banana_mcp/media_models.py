from typing import Optional
from pydantic import BaseModel

class MediaAsset(BaseModel):
    uri: str
    error: Optional[str] = None

