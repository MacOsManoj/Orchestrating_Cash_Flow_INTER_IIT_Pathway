"""
Video Generation Scheduler - Runs as background task in FastAPI
"""

import asyncio
import logging
from datetime import datetime
import schedule

from app.services.video import run_video_generation, load_metadata

logger = logging.getLogger(__name__)

# Scheduler settings
GENERATION_TIME = "06:00"  # 6 AM


def check_and_generate():
    """Check if video needs to be generated and trigger it in a non-blocking way."""
    try:
        print("[SCHEDULER] Checking if video generation needed...")
        metadata = load_metadata()
        print(
            f"[SCHEDULER] Current status: {metadata.status}, generated_at: {metadata.generated_at}"
        )

        # Check if already generated today
        if metadata.generated_at:
            generated_date = datetime.fromisoformat(metadata.generated_at).date()
            if (
                generated_date == datetime.now().date()
                and metadata.status == "completed"
            ):
                print("[SCHEDULER] Video already generated today, skipping")
                logger.info("Video already generated today, skipping")
                return

        # Check if currently generating
        if metadata.status == "generating":
            print("[SCHEDULER] Video generation already in progress, skipping")
            logger.info("Video generation already in progress, skipping")
            return

        print("[SCHEDULER] Triggering video generation...")
        logger.info("Triggering video generation (scheduled)...")
        # Schedule the blocking run_video_generation in the default ThreadPool
        loop = asyncio.get_running_loop()
        loop.create_task(loop.run_in_executor(None, run_video_generation))

    except Exception as e:
        print(f"[SCHEDULER] ERROR: {e}")
        logger.error(f"Error in scheduled video generation: {e}")


async def scheduler_loop():
    """Background scheduler loop using schedule package"""
    logger.info("Video scheduler started")

    # Schedule daily video generation at 6 AM
    schedule.every().day.at(GENERATION_TIME).do(check_and_generate)

    # Trigger on startup if not generated today (non-blocking)
    check_and_generate()

    while True:
        schedule.run_pending()
        # Sleep until next scheduled job (more efficient than fixed interval)
        next_run = schedule.idle_seconds()
        if next_run is None:
            await asyncio.sleep(60)
        elif next_run > 0:
            await asyncio.sleep(min(next_run, 3600))  # Cap at 1 hour
        else:
            await asyncio.sleep(1)


def start_scheduler():
    """Start the scheduler as a background task"""
    print(f"[SCHEDULER] Starting scheduler (daily at {GENERATION_TIME})")
    asyncio.create_task(scheduler_loop())
    logger.info(f"Video generation scheduler initialized (daily at {GENERATION_TIME})")
