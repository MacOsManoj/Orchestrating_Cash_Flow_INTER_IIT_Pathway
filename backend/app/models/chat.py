from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from bson import ObjectId


class ChatCreate(BaseModel):
    """Data required to create a new chat"""

    title: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"title": "Financial Dashboard Analysis"}}
    )


class Chat(BaseModel):
    """Chat data returned from database"""

    id: str = Field(alias="_id")
    title: str
    createdAt: datetime
    updatedAt: datetime
    currentVersionId: Optional[str] = None
    messageCount: int = 0
    isActive: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
