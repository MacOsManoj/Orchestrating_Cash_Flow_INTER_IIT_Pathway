from pymongo import MongoClient
import os

client = MongoClient("mongodb://localhost:27017/")
db = client["news_db"]

enriched_count = db["enriched_articles"].count_documents({})
summarized_count = db["summarize"].count_documents({})
irrelevant_count = db["summarize"].count_documents(
    {"is_relevant": False}
)  # Wait, irrelevant ones aren't saved to DB in the current code?

print(f"Enriched Articles in DB: {enriched_count}")
print(f"Summarized Articles in DB: {summarized_count}")

# Check if we can find the missing ones
# Get all enriched IDs
enriched_ids = set(
    doc["article_id"] for doc in db["enriched_articles"].find({}, {"article_id": 1})
)
# Get all summarized IDs
summarized_ids = set(
    doc["article_id"] for doc in db["summarize"].find({}, {"article_id": 1})
)

missing_ids = enriched_ids - summarized_ids
print(f"Missing IDs count: {len(missing_ids)}")
print(f"First 5 missing IDs: {list(missing_ids)[:5]}")
