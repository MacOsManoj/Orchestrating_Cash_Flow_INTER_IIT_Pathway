"""
Video Models - Pydantic models for video generation
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class VideoMetadata(BaseModel):
    """Metadata for a generated video"""

    id: str = Field(default_factory=lambda: date.today().isoformat(), alias="_id")
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    captions_vtt: Optional[str] = None  # VTT content stored directly
    script: Optional[str] = None
    title: str = "Daily Market Briefing"
    subtitle: str = ""
    generated_at: Optional[str] = None
    status: str = "pending"  # pending, generating, completed, failed
    error: Optional[str] = None

    class Config:
        populate_by_name = True  # Allow both 'id' and '_id'


class GenerateRequest(BaseModel):
    """Request to generate a new video"""

    force: bool = False  # Force regeneration even if already generated today


class VideoStatusResponse(BaseModel):
    """Response for video status check"""

    status: str
    generated_at: Optional[str] = None
    error: Optional[str] = None


class GenerateResponse(BaseModel):
    """Response after triggering video generation"""

    message: str
    status: str = "generating"
    metadata: Optional[VideoMetadata] = None
