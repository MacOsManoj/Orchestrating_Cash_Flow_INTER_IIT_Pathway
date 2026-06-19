# 🚀 Complete Financial Intelligence Platform - Docker Setup

Complete dockerized financial intelligence platform with news pipeline, bond analysis, forex trading, and frontend UI.

## 📋 Architecture

### Services Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (Port 80)                    │
│                    React + Vite + Nginx                      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   API BACKEND (Port 8000)                    │
│                  FastAPI + Python 3.12                       │
└──────┬──────────────────┬──────────────────────────────────┘
       │                  │
       │                  │
┌──────▼─────┐    ┌──────▼──────┐
│  Bond MCP  │    │  Forex MCP  │
│ (Port 8123)│    │ (Port 8127) │
└──────┬─────┘    └─────────────┘
       │
┌──────▼─────────────────────────────────────────────────────┐
│               BOND PIPELINE (4 Services)                     │
│         Data Collection → Processing → Forecasting          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              NEWS INTELLIGENCE PIPELINE                      │
│   Scraper → Enrichment → LLM Worker → Kafka → MongoDB       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE                             │
│         Kafka + Zookeeper + Redis + External MongoDB        │
└──────────────────────────────────────────────────────────────┘
```

## 🎯 Services

### Frontend Layer
- **frontend** - React/Vite UI (Port 80, 3000)
  - Production build with Nginx
  - API proxy to backend
  - Static asset caching

### API Layer
- **api** - FastAPI Backend (Port 8000)
  - REST API for all services
  - Health monitoring
  - CORS enabled

### MCP Servers
- **bond-mcp-server** (Port 8123)
  - Bond analysis tools
  - Forecasting data
  
- **forex-mcp-server** (Port 8127)
  - Forex trading tools
  - Market regime analysis
  - Position management

### Data Pipeline
- **bond-pipeline** - 4 background services
  - Data collection
  - Processing
  - Forecasting
  - Storage

- **news-scraper** - News metadata extraction
- **enrichment-pipeline** - Content fetching & sentiment
- **llm-worker** - Summarization & impact assessment

### Infrastructure
- **kafka** - Message streaming (Ports 9092, 9093)
- **zookeeper** - Kafka coordination (Port 2181)
- **redis** - Caching & deduplication (Port 6379)
- **MongoDB** - External (configured via MONGODB_URI)

## 🛠️ Prerequisites

1. **Docker & Docker Compose**
   ```bash
   docker --version  # >= 20.10
   docker-compose --version  # >= 2.0
   ```

2. **Environment Configuration**
   Create `backend/.env` with:
   ```bash
   # MongoDB (External - Atlas/GCP)
   MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
   
   # API Keys
   PATHWAY_LICENSE_KEY=your_pathway_license_key
   NEWSDATA_API_KEY=your_newsdata_api_key  # Optional
   
   # LLM Configuration
   OPENAI_API_KEY=your_openai_api_key
   
   # Optional: Delay for bond pipeline startup
   BOND_STARTUP_DELAY=30
   ```

## 🚀 Quick Start

### 1. Start All Services
```bash
# Start entire platform
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f frontend
docker-compose logs -f api
docker-compose logs -f bond-mcp-server
```

### 2. Access Services

- **Frontend UI**: http://localhost or http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Bond MCP**: http://localhost:8123
- **Forex MCP**: http://localhost:8127
- **Redis**: localhost:6379
- **Kafka**: localhost:9092

### 3. Health Checks

```bash
# Check all services status
docker-compose ps

# Check API health
curl http://localhost:8000/health

# Check frontend
curl http://localhost/

# Check Bond MCP
curl http://localhost:8123

# Check Forex MCP
curl http://localhost:8127/mcp/
```

## 📦 Build Individual Services

```bash
# Build specific service
docker-compose build frontend
docker-compose build api
docker-compose build bond-mcp-server
docker-compose build forex-mcp-server

# Rebuild without cache
docker-compose build --no-cache frontend
```

## 🔧 Development Workflow

### Frontend Development
```bash
# Development mode (outside Docker)
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173

# Production build test
docker-compose up --build frontend
```

### Backend Development
```bash
# Development mode (outside Docker)
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000

# Docker mode
docker-compose up --build api
```

## 🎛️ Service Management

### Start Subset of Services
```bash
# Infrastructure only
docker-compose up -d zookeeper kafka redis

# News pipeline only
docker-compose up -d news-scraper enrichment-pipeline llm-worker

# Bond services only
docker-compose up -d bond-pipeline bond-mcp-server

# Forex only
docker-compose up -d forex-mcp-server

# API + MCP servers
docker-compose up -d bond-mcp-server forex-mcp-server api

# Frontend + API
docker-compose up -d api frontend
```

### Stop Services
```bash
# Stop all
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop specific service
docker-compose stop frontend
```

## 📊 Monitoring

### View Resource Usage
```bash
docker stats

# Or specific services
docker stats frontend api bond-mcp-server
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service with tail
docker-compose logs -f --tail=100 api

# Multiple services
docker-compose logs -f frontend api
```

### Debug Container
```bash
# Execute shell in running container
docker-compose exec frontend sh
docker-compose exec api bash

# View container details
docker inspect frontend
```

## 🔍 Troubleshooting

### Common Issues

1. **Frontend can't connect to API**
   - Check API health: `curl http://localhost:8000/health`
   - Check CORS settings in docker-compose.yml
   - Verify nginx proxy config in `frontend/nginx.conf`

2. **Bond MCP not starting**
   - Check bond-pipeline logs: `docker-compose logs bond-pipeline`
   - Verify forecasts file exists: `docker-compose exec bond-pipeline ls -la /app/app/bonds_agentic_sys/output_forecasts/`
   - Increase startup timeout in healthcheck

3. **Kafka connection issues**
   - Wait for Kafka to be ready: `docker-compose logs kafka`
   - Check kafka-init completed: `docker-compose logs kafka-init`
   - Test connection: `docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092`

4. **MongoDB connection**
   - Verify MONGODB_URI in backend/.env
   - Test connection from backend: `docker-compose exec api python -c "from pymongo import MongoClient; print(MongoClient(os.environ['MONGODB_URI']).server_info())"`

5. **Port conflicts**
   ```bash
   # Check port usage
   lsof -i :80    # Frontend
   lsof -i :8000  # API
   lsof -i :8123  # Bond MCP
   lsof -i :8127  # Forex MCP
   ```

### Reset Everything
```bash
# Nuclear option - removes all containers, volumes, and images
docker-compose down -v
docker system prune -a --volumes
docker-compose up -d --build
```

## 📁 Volume Management

### Persistent Data Locations
- `bonds_cache` - Bond analysis cache
- `bonds_forecasts` - Generated forecasts
- `forex_data` - Forex historical data
- `kafka_data` - Kafka messages
- `redis_data` - Redis cache
- `pipeline_logs` - Bond pipeline logs

### Backup Volumes
```bash
# Backup bonds forecasts
docker run --rm -v upgraded-octo-spork_bonds_forecasts:/data -v $(pwd):/backup alpine tar czf /backup/bonds_forecasts.tar.gz -C /data .

# Restore
docker run --rm -v upgraded-octo-spork_bonds_forecasts:/data -v $(pwd):/backup alpine tar xzf /backup/bonds_forecasts.tar.gz -C /data
```

## 🔐 Security Considerations

1. **Environment Variables** - Never commit `.env` files
2. **API Keys** - Rotate regularly
3. **MongoDB** - Use strong passwords and IP whitelisting
4. **CORS** - Restrict origins in production
5. **Nginx** - Security headers already configured

## 📈 Performance Tuning

### Resource Limits
Each service has memory limits defined in docker-compose.yml:
- Frontend: 512MB limit, 128MB reserved
- API: 2GB limit, 512MB reserved
- Bond Pipeline: 4GB limit, 1GB reserved
- MCP Servers: 2GB limit, 512MB reserved

Adjust based on your system resources.

### Scaling
```bash
# Scale news scraper
docker-compose up -d --scale news-scraper=3

# Note: Most services are designed for single instance
# Kafka consumers handle parallelism internally
```

## 🎯 Production Deployment

1. **Update CORS origins** in docker-compose.yml
2. **Configure domain** in nginx.conf
3. **Enable HTTPS** with Let's Encrypt
4. **Use external MongoDB** (already configured)
5. **Set up monitoring** (Prometheus/Grafana)
6. **Configure log aggregation** (ELK/Loki)

## 📚 Additional Documentation

- [Bonds API](docs/BONDS_API.md)
- [Cashflow & Forex](docs/CASHFLOW+FOREX.md)
- [Orchestrator Components](docs/ORCHESTRATOR_COMPONENTS.md)
- [Stocks API](docs/STOCKS_API.md)

## 🆘 Support

For issues:
1. Check service logs: `docker-compose logs [service]`
2. Verify health checks: `docker-compose ps`
3. Review environment variables
4. Check network connectivity between services

## 📝 License

[Your License Here]
