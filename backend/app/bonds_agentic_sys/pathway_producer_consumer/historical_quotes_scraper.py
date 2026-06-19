import time
import json
import os
import sys
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
from kafka import KafkaProducer
import pathway as pw


# --- LOGGING SETUP ---
def setup_logging(log_file: str = "scraper.log"):
    """Setup logging to both console and file."""
    logger = logging.getLogger("bond_scraper")
    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


now = datetime.now()
formatted_date = now.strftime("%m/%d/%Y 00:00:00")
print(formatted_date)

# --- CONFIGURATION ---
START_DATE = "12/04/2025 00:00:00"
END_DATE = formatted_date
COUNTRY_CODE = "bx"
INDEX = 0
FREQUENCY = "P1D"
SCRAPE_INTERVAL = 2  # seconds between each page scrape

# Kafka Configuration
KAFKA_BROKERS = "pkc-619z3.us-east1.gcp.confluent.cloud:9092"
KAFKA_TOPIC_RAW_YIELDS = "raw_yields"
KAFKA_API_KEY = "BOPS3YOPIRNNHBL4"  # Set your Confluent Cloud API key
KAFKA_API_SECRET = "cfltkhIZNB7XoHOvbvVFbtDiPfdNw6+IPVi2D1I76tRy70E+2D1B9b0JqrEsdEsg"  # Set your Confluent Cloud API secret

# Page configurations with maturity mapping
PAGES_CONFIG = {
    1: {"name": "ldbmkin-01y", "maturity": 1},
    2: {"name": "ldbmkin-02y", "maturity": 2},
    5: {"name": "ldbmkin-05y", "maturity": 5},
    7: {"name": "ldbmkin-07y", "maturity": 7},
    10: {"name": "ldbmkin-10y", "maturity": 10},
}


# --- KAFKA SCHEMA ---
class KafkaYieldSchema(pw.Schema):
    date: str
    open: float
    high: float
    low: float
    close: float
    maturity: int


def get_url_for_page(page_name: str) -> str:
    """Generate URL for a specific bond page."""
    return (
        f"https://www.marketwatch.com/investing/bond/{page_name}/"
        f"downloaddatapartial?partial=true&index={INDEX}&countryCode={COUNTRY_CODE}"
        f"&iso=&startDate={START_DATE.replace(' ', '%20')}"
        f"&endDate={END_DATE.replace(' ', '%20')}"
        f"&frequency={FREQUENCY}&downloadPartial=true&csvDownload=false&newDates=false"
    )


def create_driver() -> webdriver.Chrome:
    """Create and return a Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/141.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=chrome_options)


def fetch_html_with_selenium(
    driver: webdriver.Chrome, url: str, logger: logging.Logger
) -> str:
    """Fetch HTML from URL using existing driver."""
    logger.debug(f"Fetching: {url[:80]}...")
    driver.get(url)
    time.sleep(2)  # Wait for page to load
    return driver.page_source


def parse_latest_marketwatch_row(html: str) -> dict:
    """Parse the latest row from MarketWatch table."""
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if not table:
        raise ValueError("No <table> found in HTML (likely Datadome).")

    data_rows = [tr for tr in table.find_all("tr") if tr.find_all("td")]
    if not data_rows:
        raise ValueError("No data rows (<td>) found in table.")

    first_row = data_rows[0]
    tds = first_row.find_all("td")
    if len(tds) < 5:
        raise ValueError("Not enough <td> cells to extract OHLC.")

    # Fix double date issue
    date_raw = tds[0].get_text(separator=" ", strip=True)
    m = re.search(r"\d{2}/\d{2}/\d{4}", date_raw)
    date_value = m.group(0) if m else ""

    return {
        "date": date_value,
        "open": tds[1].get_text(strip=True),
        "high": tds[2].get_text(strip=True),
        "low": tds[3].get_text(strip=True),
        "close": tds[4].get_text(strip=True),
    }


def clean_float(value: str) -> float:
    """Convert string value to float, removing % sign if present."""
    try:
        return float(value.strip().replace("%", ""))
    except (ValueError, AttributeError):
        return 0.0


def create_kafka_producer(brokers: str) -> KafkaProducer:
    """Create and return a Kafka producer with Confluent Cloud authentication."""
    return KafkaProducer(
        bootstrap_servers=brokers,
        security_protocol="SASL_SSL",
        sasl_mechanism="PLAIN",
        sasl_plain_username=KAFKA_API_KEY,
        sasl_plain_password=KAFKA_API_SECRET,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=3,
        retry_backoff_ms=100,
    )


def publish_to_kafka(
    producer: KafkaProducer, topic: str, message: dict, logger: logging.Logger
):
    """Publish a message to Kafka topic."""
    try:
        future = producer.send(topic, value=message)
        future.get(timeout=10)  # Wait for confirmation
        logger.debug(f"Published to Kafka: {message}")
    except Exception as e:
        logger.error(f"Failed to publish to Kafka: {e}")
        raise


def scrape_all_pages(producer: KafkaProducer, logger: logging.Logger) -> dict:
    """
    Scrape all configured pages with interval between each.
    Publishes data to Kafka instead of CSV.
    Returns stats dict.
    """
    stats = {"total_pages": len(PAGES_CONFIG), "success": 0, "failed": 0, "errors": []}

    # Create single driver for all pages (more efficient)
    logger.info("Starting Chrome WebDriver...")
    driver = create_driver()

    try:
        for page_id, config in PAGES_CONFIG.items():
            page_name = config["name"]
            maturity = config["maturity"]
            url = get_url_for_page(page_name)

            logger.info(
                f"[Page {page_id}] Scraping {page_name} (maturity: {maturity}y)..."
            )

            try:
                # Fetch HTML
                html = fetch_html_with_selenium(driver, url, logger)

                # Parse data
                latest = parse_latest_marketwatch_row(html)

                # Create Kafka message with schema
                kafka_message = {
                    "date": latest["date"],
                    "open": clean_float(latest["open"]),
                    "high": clean_float(latest["high"]),
                    "low": clean_float(latest["low"]),
                    "close": clean_float(latest["close"]),
                    "maturity": maturity,
                }

                # Publish to Kafka
                publish_to_kafka(
                    producer, KAFKA_TOPIC_RAW_YIELDS, kafka_message, logger
                )

                logger.info(
                    f"[Page {page_id}]  {page_name}: {latest['date']} | "
                    f"Close: {latest['close']} | Maturity: {maturity}y"
                )
                stats["success"] += 1

            except Exception as e:
                logger.error(f"[Page {page_id}] ✗ {page_name}: {e}")
                stats["failed"] += 1
                stats["errors"].append(
                    {"page": page_id, "name": page_name, "error": str(e)}
                )

            # Wait between pages (except for last one)
            if page_id != list(PAGES_CONFIG.keys())[-1]:
                logger.debug(f"Waiting {SCRAPE_INTERVAL}s before next page...")
                time.sleep(SCRAPE_INTERVAL)

    finally:
        logger.info("Closing Chrome WebDriver...")
        driver.quit()

    return stats


def run_continuous(
    producer: KafkaProducer, interval_seconds: int, logger: logging.Logger
):
    """Run scraping loop continuously, publishing to Kafka."""
    cycle = 0

    logger.info("=" * 60)
    logger.info("BOND SCRAPER - CONTINUOUS MODE (KAFKA)")
    logger.info("=" * 60)
    logger.info(f"Kafka brokers: {KAFKA_BROKERS}")
    logger.info(f"Kafka topic: {KAFKA_TOPIC_RAW_YIELDS}")
    logger.info(f"Pages to scrape: {len(PAGES_CONFIG)}")
    logger.info(f"Interval between pages: {SCRAPE_INTERVAL}s")
    logger.info(f"Interval between cycles: {interval_seconds}s")
    logger.info("=" * 60)

    while True:
        cycle += 1
        logger.info("")
        logger.info(
            f"=== CYCLE {cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ==="
        )

        start_time = time.time()
        stats = scrape_all_pages(producer, logger)
        elapsed = time.time() - start_time

        # Print cycle summary
        logger.info("")
        logger.info(
            f"Cycle {cycle} complete: {stats['success']}/{stats['total_pages']} successful ({elapsed:.1f}s)"
        )

        if stats["errors"]:
            logger.warning(f"Failed pages: {[e['name'] for e in stats['errors']]}")

        logger.info(f"Sleeping {interval_seconds}s until next cycle...")
        time.sleep(interval_seconds)


def run_once(producer: KafkaProducer, logger: logging.Logger):
    """Run scraping once for all pages, publishing to Kafka."""
    logger.info("=" * 60)
    logger.info("BOND SCRAPER - SINGLE RUN (KAFKA)")
    logger.info("=" * 60)
    logger.info(f"Kafka brokers: {KAFKA_BROKERS}")
    logger.info(f"Kafka topic: {KAFKA_TOPIC_RAW_YIELDS}")
    logger.info(f"Pages to scrape: {len(PAGES_CONFIG)}")
    logger.info("=" * 60)

    start_time = time.time()
    stats = scrape_all_pages(producer, logger)
    elapsed = time.time() - start_time

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SCRAPE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total pages:    {stats['total_pages']}")
    logger.info(f"Successful:     {stats['success']}")
    logger.info(f"Failed:         {stats['failed']}")
    logger.info(f"Time elapsed:   {elapsed:.1f}s")
    logger.info("=" * 60)

    if stats["errors"]:
        logger.info("")
        logger.warning("ERRORS:")
        for err in stats["errors"]:
            logger.warning(f"  - {err['name']}: {err['error']}")

    return stats


def main():
    import argparse

    global SCRAPE_INTERVAL, KAFKA_BROKERS, KAFKA_TOPIC_RAW_YIELDS
    parser = argparse.ArgumentParser(
        description="Scrape bond data from MarketWatch and publish to Kafka",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single run (scrape all pages once)
  python historical_quotes_scraper.py --kafka-brokers localhost:9092

  # Continuous mode (scrape every 60 seconds)
  python historical_quotes_scraper.py --kafka-brokers localhost:9092 --continuous --interval 60

  # With custom log file
  python historical_quotes_scraper.py --kafka-brokers localhost:9092 --log-file scraper.log
        """,
    )

    parser.add_argument(
        "--kafka-brokers",
        "-b",
        default=KAFKA_BROKERS,
        help=f"Kafka broker address (default: {KAFKA_BROKERS})",
    )
    parser.add_argument(
        "--kafka-topic",
        default="raw_yields",
        help="Kafka topic name (default: raw_yields)",
    )
    parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        default=True,
        help="Run continuously in a loop",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=86400,  # 24 hours
        help="Seconds between cycles in continuous mode (default: 60)",
    )
    parser.add_argument(
        "--log-file", default="scraper.log", help="Log file path (default: scraper.log)"
    )
    parser.add_argument(
        "--page-interval",
        type=int,
        default=2,
        help="Seconds between each page scrape (default: 2)",
    )

    args = parser.parse_args()

    # Update global variables
    SCRAPE_INTERVAL = args.page_interval
    KAFKA_BROKERS = args.kafka_brokers
    KAFKA_TOPIC_RAW_YIELDS = args.kafka_topic

    # Setup logging
    logger = setup_logging(args.log_file)

    try:
        # Create Kafka producer
        logger.info("Connecting to Kafka...")
        producer = create_kafka_producer(KAFKA_BROKERS)
        logger.info(f"Connected to Kafka at {KAFKA_BROKERS}")

        try:
            if args.continuous:
                run_continuous(producer, args.interval, logger)
            else:
                stats = run_once(producer, logger)
                return 0 if stats["failed"] == 0 else 1
        finally:
            logger.info("Closing Kafka producer...")
            producer.close()

    except KeyboardInterrupt:
        logger.info("\nScraper stopped by user")
        return 0
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
