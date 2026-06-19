#!/bin/bash
# Clear all caches and data from the news pipeline

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           CLEARING ALL PIPELINE CACHES & DATABASE              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Drop entire MongoDB database
echo -e "${YELLOW}🗄️  Dropping MongoDB database...${NC}"
docker exec mongodb mongosh news_db --quiet --eval "
db.dropDatabase();
print('  ✓ Database news_db dropped completely');
" 2>/dev/null && echo -e "${GREEN}  ✓ MongoDB database dropped${NC}" || echo -e "${RED}  ✗ MongoDB not accessible${NC}"
echo ""

# Clear Redis cache
echo -e "${YELLOW}🔴 Clearing Redis cache...${NC}"
docker exec redis redis-cli FLUSHALL > /dev/null 2>&1 && echo -e "${GREEN}  ✓ Redis cleared${NC}" || echo -e "${RED}  ✗ Redis not accessible${NC}"
echo ""

# Stop consumers and scraper before clearing
echo -e "${YELLOW}⏸️  Stopping consumers and scraper...${NC}"
docker compose -f docker-compose.yml stop news-scraper enrichment-pipeline llm-worker 2>/dev/null && echo -e "${GREEN}  ✓ All services stopped${NC}"
sleep 3
echo ""

# Delete consumer groups FIRST (while topics still exist)
echo -e "${YELLOW}📨 Deleting Kafka consumer groups...${NC}"
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group native-pipeline --delete 2>&1 | grep -q "Deletion of.*completed successfully" && echo -e "${GREEN}  ✓ Deleted native-pipeline group${NC}" || echo -e "${YELLOW}  ⚠ Group doesn't exist or already deleted${NC}"
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group llm-pathway-worker --delete 2>&1 | grep -q "Deletion of.*completed successfully" && echo -e "${GREEN}  ✓ Deleted llm-pathway-worker group${NC}" || echo -e "${YELLOW}  ⚠ Group doesn't exist or already deleted${NC}"
sleep 3
echo ""

# Delete Kafka topics to ensure truly fresh start
echo -e "${YELLOW}🗑️  Deleting Kafka topics...${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic raw-news-feed 2>/dev/null && echo -e "${GREEN}  ✓ Deleted raw-news-feed${NC}" || echo -e "${YELLOW}  ⚠ Topic doesn't exist${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic enriched-news 2>/dev/null && echo -e "${GREEN}  ✓ Deleted enriched-news${NC}" || echo -e "${YELLOW}  ⚠ Topic doesn't exist${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic summarized-news 2>/dev/null && echo -e "${GREEN}  ✓ Deleted summarized-news${NC}" || echo -e "${YELLOW}  ⚠ Topic doesn't exist${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic deduplicated-news 2>/dev/null && echo -e "${GREEN}  ✓ Deleted deduplicated-news${NC}" || echo -e "${YELLOW}  ⚠ Topic doesn't exist${NC}"
sleep 3
echo ""

# Recreate topics with proper configuration
echo -e "${YELLOW}📝 Recreating Kafka topics...${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic raw-news-feed --partitions 1 --replication-factor 1 2>/dev/null && echo -e "${GREEN}  ✓ Created raw-news-feed${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic enriched-news --partitions 1 --replication-factor 1 2>/dev/null && echo -e "${GREEN}  ✓ Created enriched-news${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic summarized-news --partitions 1 --replication-factor 1 2>/dev/null && echo -e "${GREEN}  ✓ Created summarized-news${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic deduplicated-news --partitions 1 --replication-factor 1 2>/dev/null && echo -e "${GREEN}  ✓ Created deduplicated-news${NC}"
sleep 2
echo ""

# Verify no consumer groups exist (double-check cleanup)
echo -e "${YELLOW}🔍 Verifying consumer groups are deleted...${NC}"
GROUP_COUNT=$(docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list 2>/dev/null | grep -E "native-pipeline|llm-native-worker" | wc -l)
if [ "$GROUP_COUNT" -eq 0 ]; then
    echo -e "${GREEN}  ✓ No consumer groups found (clean state)${NC}"
else
    echo -e "${RED}  ✗ WARNING: Found $GROUP_COUNT consumer groups still active!${NC}"
    docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list 2>/dev/null | grep -E "native-pipeline|llm-native-worker"
fi
echo ""

# Don't restart - leave stopped for manual testing
echo -e "${YELLOW}⏸️  Services remain stopped${NC}"
echo -e "  ℹ️  Run 'docker compose -f docker-compose.yml start news-scraper enrichment-pipeline llm-worker' to restart"
echo ""

# Clear Bloom filter and application caches
echo -e "${YELLOW}🧹 Clearing application caches and Bloom filters...${NC}"
docker exec enrichment-pipeline rm -rf /app/.cache/* 2>/dev/null && echo -e "${GREEN}  ✓ Pipeline cache cleared${NC}" || echo -e "  ℹ️  No cache to clear"
docker exec news-scraper bash -c "rm -rf /app/.cache/* && python -c 'import redis; r=redis.Redis(host=\"redis\", port=6379, decode_responses=True); keys=r.keys(\"bloom:*\"); [r.delete(k) for k in keys]; print(f\"  ✓ Deleted {len(keys)} Bloom filter keys from Redis\")'" 2>/dev/null && echo -e "${GREEN}  ✓ News scraper cache and Bloom filters cleared${NC}" || echo -e "  ℹ️  No cache to clear"
echo -e "${GREEN}  ✓ LLM worker (Pathway) has no file cache${NC}"
echo ""

# Verify cleanup
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Database, Kafka topics, and all caches cleared!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "To verify, run: ${YELLOW}./scripts/monitor.sh${NC}"
echo ""
