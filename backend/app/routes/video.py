"""
Video API Routes - Serves video metadata and triggers generation
"""

import logging
from datetime import datetime, date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.models.video import (
    VideoMetadata,
    GenerateRequest,
    VideoStatusResponse,
    GenerateResponse,
)
from app.services.video import load_metadata_async, run_video_generation, OUTPUT_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/latest", response_model=VideoMetadata)
async def get_latest_video():
    """Get the latest video metadata"""
    metadata = await load_metadata_async()
    return metadata


@router.get("/file")
async def get_video_file():
    """Serve the video file directly"""
    video_path = OUTPUT_DIR / "news.mp4"

    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(video_path, media_type="video/mp4")


@router.get("/captions")
async def get_captions_file():
    """Serve the WebVTT captions from MongoDB"""
    metadata = await load_metadata_async()

    if not metadata.captions_vtt:
        raise HTTPException(status_code=404, detail="Captions not found")

    from fastapi.responses import Response

    return Response(
        content=metadata.captions_vtt,
        media_type="text/vtt",
        headers={"Content-Type": "text/vtt; charset=utf-8"},
    )


@router.post("/generate", response_model=GenerateResponse)
async def trigger_generation(
    background_tasks: BackgroundTasks, request: GenerateRequest = GenerateRequest()
):
    """Trigger video generation (runs in background)"""
    metadata = await load_metadata_async()

    # Check if already generated today
    if metadata.generated_at and not request.force:
        generated_date = datetime.fromisoformat(metadata.generated_at).date()
        if generated_date == date.today() and metadata.status == "completed":
            return GenerateResponse(
                message="Video already generated today",
                status=metadata.status,
                metadata=metadata,
            )

    # Check if currently generating
    if metadata.status == "generating":
        return GenerateResponse(
            message="Video generation already in progress",
            status=metadata.status,
            metadata=metadata,
        )

    # Start background generation
    background_tasks.add_task(run_video_generation)

    logger.info("Video generation triggered")
    return GenerateResponse(message="Video generation started", status="generating")


@router.get("/status", response_model=VideoStatusResponse)
async def get_generation_status():
    """Get current generation status"""
    metadata = await load_metadata_async()
    return VideoStatusResponse(
        status=metadata.status, generated_at=metadata.generated_at, error=metadata.error
    )


@router.get("/history")
async def get_video_history(limit: int = 7):
    """Get video generation history for the past N days"""
    from app.database import get_database

    db = get_database()
    cursor = db["video_metadata"].find().sort("_id", -1).limit(limit)

    history = []
    async for doc in cursor:
        history.append(VideoMetadata(**doc))

    return history
