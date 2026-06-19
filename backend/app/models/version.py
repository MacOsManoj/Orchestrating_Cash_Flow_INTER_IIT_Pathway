from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional



class VersionCreate(BaseModel):
    prompt: str
    versionNumber: int


class Version(BaseModel):
    id: str = Field(alias="_id")
    chatId: str
    versionNumber: int
    prompt: str
    message: Optional[str] = None          # 🆕 agent message text
    components: List[Dict[str, Any]]
    createdAt: datetime

    class Config:
        populate_by_name = True
