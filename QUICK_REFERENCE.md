# 🚀 Quick Reference Guide

## One-Line Commands

```bash
# Validate setup
./validate.sh

# Start everything
./platform.sh start

# Stop everything
./platform.sh stop

# View all logs
./platform.sh logs

# Check health
./platform.sh health

# See all URLs
./platform.sh urls
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost | Main dashboard |
| **Frontend** | http://localhost:3000 | Alternative port |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **API Health** | http://localhost:8000/health | Health check endpoint |
| **Bond MCP** | http://localhost:8123 | Bond analysis server |
| **Forex MCP** | http://localhost:8127 | Forex trading server |
| **Kafka** | localhost:9092 | Internal message broker |
| **Redis** | localhost:6379 | Internal cache |

## Essential Commands

### Startup

```bash
# Full platform
./platform.sh start

# Core only (API + Frontend + MCP servers)
./platform.sh start-core

# Infrastructure only
./platform.sh start-infra

# News pipeline only
./platform.sh start-news
```

### Monitoring

```bash
# Service status
./platform.sh status
docker-compose ps

# View logs
./platform.sh logs              # All services
./platform.sh logs frontend     # Specific service
./platform.sh logs api

# Resource usage
./platform.sh resources
docker stats

# Health check
./platform.sh health
curl http://localhost:8000/health
```

### Troubleshooting

```bash
# Restart specific service
docker-compose restart frontend
docker-compose restart api

# Rebuild and restart
./platform.sh rebuild frontend
./platform.sh rebuild api

# View service details
docker inspect frontend
docker-compose exec frontend sh

# Check logs for errors
docker-compose logs --tail=100 api | grep -i error
docker-compose logs --tail=100 frontend | grep -i error
```

### Cleanup

```bash
# Stop all
./platform.sh stop

# Remove everything including volumes
./platform.sh clean

# Remove unused Docker resources
docker system prune -a
```

## Environment Variables

### Required in `backend/.env`

```bash
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
PATHWAY_LICENSE_KEY=your_pathway_license_key
OPENAI_API_KEY=your_openai_api_key
```

### Optional in `backend/.env`

```bash
NEWSDATA_API_KEY=your_newsdata_api_key
BOND_STARTUP_DELAY=30
```

## Common Issues & Fixes

### Frontend can't connect to API

```bash
# Check API is running
curl http://localhost:8000/health

# Check CORS settings
docker-compose logs api | grep CORS

# Restart API
docker-compose restart api
```

### Port already in use

```bash
# Find what's using the port
lsof -i :80    # Frontend
lsof -i :8000  # API

# Stop conflicting service or change port in docker-compose.yml
```

### Services not healthy

```bash
# Check health status
docker-compose ps

# View specific service logs
./platform.sh logs bond-mcp-server
./platform.sh logs forex-mcp-server

# Wait longer (services have startup delays)
sleep 30 && ./platform.sh health
```

### Out of memory

```bash
# Check current usage
docker stats

# Reduce resource limits in docker-compose.yml
# Or increase system memory
```

### Kafka connection failed

```bash
# Check Kafka is healthy
docker-compose logs kafka

# Restart Kafka
docker-compose restart zookeeper kafka

# Recreate Kafka topics
docker-compose up -d kafka-init
```

## Development Workflow

### Frontend Development

```bash
# Option 1: Local development (hot reload)
cd frontend
npm install
npm run dev  # http://localhost:5173

# Option 2: Docker with rebuild
docker-compose up --build frontend
```

### Backend Development

```bash
# Option 1: Local development
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000

# Option 2: Docker with live reload (volume mount)
docker-compose up api
# Edit files, they're synced via volumes
```

### Testing Changes

```bash
# Rebuild specific service
./platform.sh rebuild frontend
./platform.sh rebuild api

# Or rebuild all
docker-compose build
docker-compose up -d
```

## Data Management

### Backup Data

```bash
# Automated backup
./platform.sh backup

# Manual backup
docker run --rm \
  -v upgraded-octo-spork_bonds_forecasts:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/bonds_forecasts.tar.gz -C /data .
```

### View Volumes

```bash
# List all volumes
docker volume ls | grep upgraded-octo-spork

# Inspect specific volume
docker volume inspect upgraded-octo-spork_bonds_forecasts

# Remove unused volumes
docker volume prune
```

## Performance Tuning

### Scale Services

```bash
# Not recommended - most services are designed for single instance
# But can scale stateless services:
docker-compose up -d --scale news-scraper=2
```

### Resource Limits

Edit `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 2G  # Increase if needed
    reservations:
      memory: 512M
```

### Clear Caches

```bash
# Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Docker build cache
docker builder prune -a
```

## Production Checklist

- [ ] Update CORS origins in docker-compose.yml
- [ ] Configure proper MongoDB connection string
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure domain in nginx.conf
- [ ] Set resource limits appropriately
- [ ] Enable monitoring (Prometheus/Grafana)
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Configure backups
- [ ] Test disaster recovery
- [ ] Document runbooks

## Getting Help

1. **Check logs first**: `./platform.sh logs [service]`
2. **Verify health**: `./platform.sh health`
3. **Review environment**: Check backend/.env
4. **Check resources**: `./platform.sh resources`
5. **Consult docs**: See DOCKER_DEPLOYMENT.md

## Useful Docker Commands

```bash
# View all containers
docker ps -a

# Remove stopped containers
docker container prune

# View images
docker images

# Remove unused images
docker image prune -a

# View networks
docker network ls

# Inspect network
docker network inspect intelligence_network

# Execute command in container
docker-compose exec api bash
docker-compose exec frontend sh

# Copy files from container
docker cp frontend:/usr/share/nginx/html/index.html .

# View container logs with timestamps
docker-compose logs -f -t api
```

## Emergency Commands

```bash
# Nuclear option - reset everything
docker-compose down -v
docker system prune -a --volumes -f
./platform.sh start

# Force remove all containers
docker rm -f $(docker ps -aq)

# Force remove all volumes
docker volume rm $(docker volume ls -q)

# Restart Docker daemon (Linux)
sudo systemctl restart docker
```

---

**Pro Tip**: Always run `./validate.sh` before starting the platform to catch configuration issues early!
