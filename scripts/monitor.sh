#!/bin/bash
# News Pipeline Monitoring Script

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           NEWS PIPELINE MONITORING DASHBOARD                   ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if containers are running
echo -e "${YELLOW}📊 Container Status:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAMES|kafka|mongodb|redis|news-scraper|enrichment-pipeline|llm-worker" || echo "No containers running"
echo ""

# Pathway Pipeline Metrics
echo -e "${YELLOW}📈 Pathway Pipeline Metrics:${NC}"
docker exec enrichment-pipeline python -c "
import requests
try:
    # Try localhost first, then 0.0.0.0
    for host in ['localhost', '127.0.0.1', '0.0.0.0']:
        try:
            r = requests.get(f'http://{host}:8080/metrics', timeout=2)
            if r.status_code == 200:
                metrics = {}
                for line in r.text.split('\n'):
                    if 'rows_positive' in line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) == 2:
                            key = parts[0].replace('_rows_positive', '')
                            metrics[key] = int(parts[1])
                
                total_processed = sum(metrics.values())
                print(f'  ✓ Monitoring endpoint: http://{host}:8080')
                print(f'  Total rows processed: {total_processed}')
                print(f'  Pipeline operators: {len(metrics)}')
                if metrics:
                    print(f'  Sample metrics: {dict(list(metrics.items())[:3])}')
                break
        except:
            continue
    else:
        raise Exception('Monitoring endpoint not accessible on any interface')
except Exception as e:
    print(f'  ⚠️  Metrics endpoint not ready: {e}')
    print(f'  Pipeline may still be initializing. Check logs: docker logs enrichment-pipeline')
" 2>/dev/null || echo "  ❌ Pathway pipeline not responding"
echo ""

# MongoDB Stats (via API since using Atlas)
echo -e "${YELLOW}📚 MongoDB Statistics (via API):${NC}"
curl -s http://localhost:8000/api/news/stats 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  ⚠️  API not responding - use 'curl http://localhost:8000/api/news/stats' to check"
echo ""

# Redis Stats
echo -e "${YELLOW}🔴 Redis Cache Stats:${NC}"
docker exec redis redis-cli INFO stats | grep -E "total_commands_processed|total_connections_received|keyspace_hits|keyspace_misses" | sed 's/^/  /' || echo "  ❌ Redis not accessible"
echo ""

# Kafka Topics
echo -e "${YELLOW}📨 Kafka Topics Status:${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | sed 's/^/  /' || echo "  ❌ Kafka not accessible"
echo ""

# Kafka Consumer Lag
echo -e "${YELLOW}🔄 Kafka Consumer Lag:${NC}"
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --all-groups 2>/dev/null | grep -E "GROUP|native-pipeline|llm-summarization" | head -10 | sed 's/^/  /' || echo "  ❌ No consumer groups found"
echo ""

# Recent Logs
echo -e "${YELLOW}📝 Recent Pipeline Activity (last 5 lines):${NC}"
echo -e "${GREEN}News Scraper:${NC}"
docker logs news-scraper --tail 3 2>/dev/null | sed 's/^/  /' || echo "  ❌ No logs"
echo ""
echo -e "${GREEN}Pathway Pipeline:${NC}"
docker logs enrichment-pipeline --tail 3 2>/dev/null | sed 's/^/  /' || echo "  ❌ No logs"
echo ""
echo -e "${GREEN}LLM Worker:${NC}"
docker logs llm-worker --tail 3 2>/dev/null | sed 's/^/  /' || echo "  ❌ No logs"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "💡 For detailed MongoDB queries, run: ${GREEN}./scripts/query-news.sh${NC}"
echo -e "💡 For live logs, run: ${GREEN}./scripts/logs.sh${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
