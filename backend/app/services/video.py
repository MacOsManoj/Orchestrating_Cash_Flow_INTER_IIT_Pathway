"""
Video Generation Service - Handles HeyGen video generation and script creation
"""

import json
import time
import logging
import requests
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from pymongo import MongoClient

from app.models.video import VideoMetadata
from app.config import settings

logger = logging.getLogger(__name__)

# Base directory (backend folder)
BASE_DIR = Path(__file__).resolve().parents[2]

# Output directory for generated videos (placed under backend/video_generated)
OUTPUT_DIR = BASE_DIR / "video_generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# MongoDB collection name for video metadata
VIDEO_COLLECTION = "video_metadata"


def generate_vtt_from_script(script: str, words_per_minute: int = 150) -> str:
    """
    Generate WebVTT subtitle file from script text.

    Splits script into sentences and estimates timing based on word count.
    Average speaking rate is ~150 words per minute.
    """
    # Split script into sentences
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    # Calculate timing
    words_per_second = words_per_minute / 60

    vtt_lines = ["WEBVTT\n"]
    current_time = 0.0

    for i, sentence in enumerate(sentences):
        word_count = len(sentence.split())
        duration = max(
            word_count / words_per_second, 2.0
        )  # Minimum 2 seconds per caption

        start_time = current_time
        end_time = current_time + duration

        # Format timestamps as HH:MM:SS.mmm
        start_str = format_vtt_timestamp(start_time)
        end_str = format_vtt_timestamp(end_time)

        vtt_lines.append(f"\n{i + 1}")
        vtt_lines.append(f"{start_str} --> {end_str}")
        vtt_lines.append(sentence)

        current_time = end_time

    return "\n".join(vtt_lines)


def format_vtt_timestamp(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def get_sync_db():
    """Get synchronous MongoDB client for use in background tasks"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB]


def load_metadata(target_date: Optional[date] = None) -> VideoMetadata:
    """Load video metadata from MongoDB for a specific date (defaults to today)"""
    target_date = target_date or date.today()
    doc_id = target_date.isoformat()

    try:
        db = get_sync_db()
        doc = db[VIDEO_COLLECTION].find_one({"_id": doc_id})

        if doc:
            return VideoMetadata(**doc)

        # Return default metadata for this date
        return VideoMetadata(id=doc_id)
    except Exception as e:
        logger.warning(f"Failed to load metadata from MongoDB: {e}")
        return VideoMetadata(id=doc_id)


def save_metadata(metadata: VideoMetadata) -> None:
    """Save video metadata to MongoDB"""
    try:
        db = get_sync_db()
        doc = metadata.model_dump(by_alias=True)

        # Upsert: update if exists, insert if not
        db[VIDEO_COLLECTION].replace_one({"_id": doc["_id"]}, doc, upsert=True)
        logger.info(f"Saved video metadata for {doc['_id']}")
    except Exception as e:
        logger.error(f"Failed to save metadata to MongoDB: {e}")
        raise


async def load_metadata_async(target_date: Optional[date] = None) -> VideoMetadata:
    """Async version: Load video metadata from MongoDB"""
    from app.database import get_database

    target_date = target_date or date.today()
    doc_id = target_date.isoformat()

    try:
        db = get_database()
        doc = await db[VIDEO_COLLECTION].find_one({"_id": doc_id})

        if doc:
            return VideoMetadata(**doc)

        return VideoMetadata(id=doc_id)
    except Exception as e:
        logger.warning(f"Failed to load metadata from MongoDB: {e}")
        return VideoMetadata(id=doc_id)


async def save_metadata_async(metadata: VideoMetadata) -> None:
    """Async version: Save video metadata to MongoDB"""
    from app.database import get_database

    try:
        db = get_database()
        doc = metadata.model_dump(by_alias=True)

        await db[VIDEO_COLLECTION].replace_one({"_id": doc["_id"]}, doc, upsert=True)
        logger.info(f"Saved video metadata for {doc['_id']}")
    except Exception as e:
        logger.error(f"Failed to save metadata to MongoDB: {e}")
        raise


def get_asset_id() -> Optional[str]:
    """Upload background image and get asset ID from HeyGen.

    Search a few candidate locations inside the backend for a background image.
    If none is found, return None — the video payload will omit the background.
    """
    image_path = BASE_DIR / "assets" / "news-bg.png"

    if not image_path.exists():
        print(
            f"[HEYGEN] No background image found at {image_path}, proceeding without background"
        )
        logger.warning(
            "No background image found at %s, proceeding without background", image_path
        )
        return None

    print(f"[HEYGEN] Uploading background image from {image_path}...")
    with open(image_path, "rb") as f:
        response = requests.post(
            "https://upload.heygen.com/v1/asset",
            data=f,
            headers={"Content-Type": "image/png", "x-api-key": settings.HEYGEN_API_KEY},
        )
        print(
            f"[HEYGEN] Asset upload response: {response.status_code} - {response.text[:200]}"
        )
        response.raise_for_status()
        asset_id = response.json()["data"]["id"]
        print(f"[HEYGEN] Got asset_id: {asset_id}")
        return asset_id


def create_gemini_prompt(news: list) -> str:
    """Create prompt for Gemini to generate video script"""
    return f"""
You are a professional news reporter.

Summary of today's news:
{json.dumps(news, indent=2)}

Based on the above news snippets, create a script for a 1-2 minute video summarizing the key points.
DO NOT hallucinate or use any other information other than the above data.

Keep tone natural, fluent, and professional.
Return only the script text, no JSON formatting.
"""


def get_script(processed_news: list) -> str:
    """Generate script using Gemini AI"""
    print("[GEMINI] Generating script with Gemini...")
    print(f"[GEMINI] API Key (first 10 chars): {settings.GEMINI_API_KEY[:10]}...")
    print(f"[GEMINI] Processing {len(processed_news)} news items")

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(create_gemini_prompt(processed_news))
        script = response.text
        print(f"[GEMINI] Script generated successfully ({len(script)} chars)")
        print(f"[GEMINI] Script preview: {script[:200]}...")
        return script
    except Exception as e:
        print(f"[GEMINI] ERROR: {type(e).__name__}: {e}")
        raise


def process_news_result(result: list) -> list:
    """Process news articles for script generation"""
    processed = []
    for row in result:
        processed.append(
            {
                "summary": row.get("summary", ""),
                "key_points": row.get("key_points", []),
                "impact_assessment": row.get("impact_assessment", ""),
            }
        )
    return processed


def generate_heygen_video(script: str, metadata: VideoMetadata) -> None:
    """Generate video using HeyGen API"""
    print("[HEYGEN] Starting HeyGen video generation...")

    try:
        asset_id = get_asset_id()
        print(f"[HEYGEN] Asset ID: {asset_id}")
    except FileNotFoundError as e:
        print(f"[HEYGEN] ERROR: Asset upload failed (FileNotFound): {e}")
        logger.error(f"Asset upload failed: {e}")
        metadata.status = "failed"
        metadata.error = str(e)
        save_metadata(metadata)
        return
    except Exception as e:
        print(f"[HEYGEN] ERROR: Asset upload failed: {e}")
        logger.error(f"Asset upload failed: {e}")
        metadata.status = "failed"
        metadata.error = f"Failed to upload background image: {e}"
        save_metadata(metadata)
        return

    url = "https://api.heygen.com/v2/video/generate"
    headers = {"X-Api-Key": settings.HEYGEN_API_KEY, "Content-Type": "application/json"}

    # Build video input; include background only if asset_id is available
    video_input = {
        "character": {
            "type": "avatar",
            "avatar_id": settings.HEYGEN_AVATAR_ID,
            "avatar_style": "normal",
        },
        "voice": {
            "type": "text",
            "input_text": script,
            "voice_id": settings.HEYGEN_VOICE_ID,
            "speed": 1,
        },
    }

    if asset_id:
        video_input["background"] = {"type": "image", "image_asset_id": asset_id}

    payload = {
        "video_inputs": [video_input],
        "dimension": {"width": 1280, "height": 720},
    }

    print(f"[HEYGEN] Request URL: {url}")
    print(f"[HEYGEN] Avatar ID: {settings.HEYGEN_AVATAR_ID}")
    print(f"[HEYGEN] Voice ID: {settings.HEYGEN_VOICE_ID}")
    print(f"[HEYGEN] Script length: {len(script)} chars")
    print(f"[HEYGEN] API Key (first 10 chars): {settings.HEYGEN_API_KEY[:10]}...")

    try:
        print("[HEYGEN] Sending POST request to generate video...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        print(f"[HEYGEN] Response status: {response.status_code}")
        print(f"[HEYGEN] Response body: {response.text[:500]}")

        if response.status_code != 200:
            print(f"[HEYGEN] ERROR: API returned non-200 status")
            metadata.status = "failed"
            metadata.error = f"HeyGen API error: {response.text}"
            save_metadata(metadata)
            return

        video_id = response.json()["data"]["video_id"]
        print(f"[HEYGEN] Video ID: {video_id}")
        video_status_url = (
            f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
        )

        # Poll for completion
        poll_count = 0
        while True:
            poll_count += 1
            print(f"[HEYGEN] Polling status (attempt {poll_count})...")
            status_response = requests.get(
                video_status_url, headers=headers, timeout=30
            )
            print(f"[HEYGEN] Status response: {status_response.status_code}")

            data = status_response.json()["data"]
            status = data["status"]
            print(f"[HEYGEN] Video status: {status}")

            if status == "completed":
                video_url = data["video_url"]
                thumbnail_url = data["thumbnail_url"]
                print(f"[HEYGEN] Video completed! URL: {video_url}")

                # Download video locally
                print("[HEYGEN] Downloading video file...")
                video_filename = OUTPUT_DIR / "news.mp4"
                with open(video_filename, "wb") as video_file:
                    video_content = requests.get(video_url).content
                    video_file.write(video_content)
                print(f"[HEYGEN] Video saved to {video_filename}")

                # Update metadata
                metadata.video_url = video_url
                metadata.thumbnail_url = thumbnail_url
                metadata.status = "completed"
                metadata.generated_at = datetime.now().isoformat()
                metadata.subtitle = f"Generated on {date.today().strftime('%B %d, %Y')}"
                metadata.error = None
                save_metadata(metadata)

                print("[HEYGEN] Video generation COMPLETE!")
                logger.info(f"Video generated successfully: {video_url}")
                break

            elif status in ("processing", "pending"):
                print(f"[HEYGEN] Still {status}, waiting 20 seconds...")
                logger.info(f"Video status: {status}, waiting...")
                time.sleep(20)

            elif status == "failed":
                error_msg = data.get("error", "Unknown error")
                print(f"[HEYGEN] ERROR: Video generation failed: {error_msg}")
                metadata.status = "failed"
                metadata.error = error_msg
                save_metadata(metadata)
                logger.error(f"Video generation failed: {metadata.error}")
                break

    except Exception as e:
        print(f"[HEYGEN] EXCEPTION: {type(e).__name__}: {e}")
        logger.error(f"HeyGen video generation failed: {e}")
        metadata.status = "failed"
        metadata.error = str(e)
        save_metadata(metadata)


def run_video_generation() -> None:
    """Main video generation workflow"""
    print("[VIDEO] Starting video generation workflow...")
    logger.info("Starting video generation workflow...")

    metadata = load_metadata()
    metadata.status = "generating"
    save_metadata(metadata)

    try:
        # Fetch today's news
        print(f"[VIDEO] Fetching news from {settings.NEWS_API_URL}")
        logger.info(f"Fetching news from {settings.NEWS_API_URL}")
        params = {"start_date": date.today().isoformat(), "limit": 10}
        response = requests.get(settings.NEWS_API_URL, params=params, timeout=30)

        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch news: {response.status_code} - {response.text}"
            )

        result = response.json()
        print(f"[VIDEO] Got {len(result)} news articles")
        logger.info(f"Got {len(result)} news articles")

        if not result:
            raise Exception("No news articles found for today")

        # Process and generate script
        print("[VIDEO] Processing news and generating script...")
        processed = process_news_result(result)
        script = get_script(processed)

        print(f"[VIDEO] Generated script with {len(script)} characters")
        logger.info(f"Generated script with {len(script)} characters")

        # Save script and generate captions VTT content
        metadata.script = script
        metadata.captions_vtt = generate_vtt_from_script(script)
        print("[VIDEO] Captions VTT generated")

        # Generate video
        print("[VIDEO] Calling HeyGen API...")
        generate_heygen_video(script, metadata)

    except Exception as e:
        print(f"[VIDEO] ERROR: Video generation workflow failed: {e}")
        logger.error(f"Video generation workflow failed: {e}")
        metadata.status = "failed"
        metadata.error = str(e)
        save_metadata(metadata)
