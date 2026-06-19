#!/usr/bin/env python3
"""
Bond Server Auto-Restart Manager (Python version)
Cross-platform alternative to bash scripts
"""

import os
import sys
import time
import signal
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Get script directory to make all paths relative
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)  # Change to script directory so relative paths work

# Configuration
SERVER_SCRIPT = "bond_server.py"
FORECAST_FILE = "../output_forecasts/final_forecasts.csv"
LOG_FILE = "logs/bond_server_manager.log"
RESTART_INTERVAL = 24 * 60 * 60  # 24 hours in seconds
CHECK_INTERVAL = 60  # Check every 60 seconds
ENABLE_FILE_MONITORING = True  # Set to False for basic 24h-only restart

# Setup logging
log_dir = Path(LOG_FILE).parent
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Global variables
server_process = None
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info("Shutdown signal received...")
    shutdown_requested = True
    stop_server()
    logger.info("✓ Cleanup complete")
    sys.exit(0)


def stop_server():
    """Stop the server process"""
    global server_process
    if server_process and server_process.poll() is None:
        logger.info(f"   Stopping server (PID: {server_process.pid})...")
        server_process.terminate()
        try:
            server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("   Server didn't stop gracefully, forcing...")
            server_process.kill()
        server_process = None


def start_server():
    """Start the bond server"""
    global server_process

    if not Path(SERVER_SCRIPT).exists():
        logger.error(f"ERROR: {SERVER_SCRIPT} not found")
        return False

    logger.info("")
    logger.info("=" * 60)
    logger.info("Starting Bond Server")

    # Get forecast file info
    if Path(FORECAST_FILE).exists():
        mtime = Path(FORECAST_FILE).stat().st_mtime
        mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"   Forecast file: Last modified {mod_time}")
    else:
        logger.info("   WARNING: Forecast file not found yet")

    logger.info("=" * 60)

    try:
        server_process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"✓ Server started (PID: {server_process.pid})")
        return True
    except Exception as e:
        logger.error(f"ERROR: Failed to start server: {e}")
        return False


def get_file_mtime(filepath):
    """Get file modification time"""
    try:
        return Path(filepath).stat().st_mtime
    except:
        return None


def monitor_server():
    """
    Monitor the server and decide when to restart.
    Returns:
        1 = Server crashed
        2 = New data detected
        3 = 24-hour scheduled restart
    """
    global server_process, shutdown_requested

    start_time = time.time()
    next_restart_time = start_time + RESTART_INTERVAL
    last_forecast_mtime = get_file_mtime(FORECAST_FILE)

    iteration = 0

    while not shutdown_requested:
        time.sleep(CHECK_INTERVAL)
        iteration += 1

        # Check if server is still running
        if server_process.poll() is not None:
            logger.warning("WARNING: Server crashed! Restarting in 10 seconds...")
            time.sleep(10)
            return 1

        # Check for new forecast data
        if ENABLE_FILE_MONITORING and Path(FORECAST_FILE).exists():
            current_mtime = get_file_mtime(FORECAST_FILE)

            if current_mtime and current_mtime != last_forecast_mtime:
                mod_time = datetime.fromtimestamp(current_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                logger.info("NEW DATA DETECTED!")
                logger.info(f"   Forecast updated: {mod_time}")
                logger.info("   Triggering restart to load fresh data...")
                return 2

        # Check if 24 hours elapsed
        if time.time() >= next_restart_time:
            logger.info("24-hour scheduled restart")
            return 3

        # Log status every 10 minutes
        if iteration % 10 == 0:
            elapsed = time.time() - start_time
            hours_running = int(elapsed / 3600)
            minutes_running = int((elapsed % 3600) / 60)

            time_remaining = next_restart_time - time.time()
            hours_remaining = int(time_remaining / 3600)

            logger.info(
                f"Running: {hours_running}h {minutes_running}m | "
                f"Next restart: {hours_remaining}h"
            )


def main():
    """Main execution loop"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║  Bond Server Auto-Restart Manager (Python)              ║")
    if ENABLE_FILE_MONITORING:
        logger.info("║  Mode: Smart (restarts on new data OR every 24h)        ║")
    else:
        logger.info("║  Mode: Basic (restarts every 24h only)                  ║")
    logger.info("╚" + "=" * 58 + "╝")

    restart_count = 0

    while not shutdown_requested:
        restart_count += 1

        if not start_server():
            logger.error("Failed to start server. Retrying in 30 seconds...")
            time.sleep(30)
            continue

        restart_reason = monitor_server()

        if shutdown_requested:
            break

        # Stop the server before restart
        stop_server()

        # Log restart reason
        if restart_reason == 1:
            logger.warning("WARNING: Restart due to server crash")
        elif restart_reason == 2:
            logger.info("✓ Restart due to new forecast data")
        elif restart_reason == 3:
            logger.info("✓ Restart due to 24-hour schedule")

        # Brief pause before restart
        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
