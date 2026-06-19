# Financial Intelligence Platform - Team 46

## 🎯 Features

### News Intelligence

- **Automated News Collection**: Scrapes financial news from Google News RSS
- **Multi-layer Deduplication**: URL, content, and fuzzy title matching
- **Sentiment Analysis**: FinBERT-based sentiment classification
- **LLM Summarization**: AI-powered article summarization and impact assessment
- **Story Clustering**: Groups related articles from multiple sources

### Bond Analysis

- **Real-time Forecasting**: 14-day yield predictions using Pathway
- **MCP Server**: Bond analysis tools and data access
- **Nelson-Siegel Model**: Yield curve fitting and interpolation
- **Price Calculation**: Dirty bond prices for multiple maturities

### Forex Trading

- **Market Regime Analysis**: Hurst exponent for trend detection
- **Position Management**: Trade history and performance tracking
- **Currency Correlation**: Multi-pair correlation analysis
- **News Sentiment**: Impact on forex pairs

### Frontend Dashboard

- **Interactive UI**: React-based trading dashboard
- **Real-time Updates**: Live data from backend services
- **Multi-view Layout**: Bonds, Forex, News, and Performance views
- **Responsive Design**: Works on desktop and tablet

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React/Vite)                     │
│                         Port 80/3000                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   API (FastAPI) - Port 8000                  │
└──────┬──────────────────┬──────────────────────────────────┘
       │                  │
┌──────▼─────┐    ┌──────▼──────┐
│  Bond MCP  │    │  Forex MCP  │
│    8123    │    │     8127    │
└──────┬─────┘    └─────────────┘
       │
┌──────▼─────────────────────────────────────────────────────┐
│                   BOND PIPELINE (4 Services)                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              NEWS PIPELINE (Scraper → Enrichment → LLM)      │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│         INFRASTRUCTURE (Kafka, Redis, External MongoDB)      │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start with Docker

The entire platform runs in Docker containers for easy deployment.

### Prerequisites

- Docker & Docker Compose (20.10+)
- MongoDB Atlas account or external MongoDB
- API Keys (see Environment Setup below)
- 16GB+ RAM recommended

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/upgraded-octo-spork.git
cd upgraded-octo-spork
```

### Prerequisites - Get Your API Keys

Before setting up the environment, you'll need these free/paid API keys:

| Service                                                  | Free Tier             | Required? | Purpose                          |
| -------------------------------------------------------- | --------------------- | --------- | -------------------------------- |
| [Google Gemini](https://aistudio.google.com/app/apikeys) | ✅ Yes (free)         | ⭐ Yes    | Article summarization & analysis |
| [OpenAI](https://platform.openai.com/api-keys)           | ❌ No ($5+ credit)    | ⭐ Yes    | GPT-4o for orchestration & bonds |
| [NewsData.io](https://newsdata.io)                       | ✅ Yes (free)         | ⭐ Yes    | News feed enrichment             |
| [Groq](https://console.groq.com)                         | ✅ Yes (free)         | Optional  | Faster LLM inference             |
| [SerpAPI](https://serpapi.com)                           | ✅ Yes (limited free) | Optional  | Web search for bonds             |
| [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)     | ✅ Yes (free)         | ⭐ Yes    | Database (cloud hosted)          |

### API Key Setup Instructions

#### 1️⃣ MongoDB Atlas (Database - Required)

```bash
# 1. Create free account: https://www.mongodb.com/cloud/atlas/register
# 2. Create a cluster (M0 free tier is perfect for development)
# 3. Go to Database Access → Add New User
#    - Username: your_username
#    - Password: your_password
#    - Built-in Role: Read and write to any database
# 4. Go to Network Access → Add IP Address
#    - Add 0.0.0.0/0 (allows all IPs - OK for development)
# 5. Go to Databases → Connect → Drivers
#    - Copy the connection string
# 6. Format: mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/dbname?retryWrites=true

MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/news_db?retryWrites=true
```

#### 2️⃣ Google Gemini API (Article Summarization - Required)

```bash
# 1. Visit: https://aistudio.google.com/app/apikeys
# 2. Click "Create API Key"
# 3. Choose "Create API key in new project"
# 4. Copy the key that looks like: AIzaSyX...

GEMINI_API_KEY=AIzaSyX...your_key_here
```

#### 3️⃣ OpenAI API (GPT Models - Required)

```bash
# 1. Sign up/login: https://platform.openai.com
# 2. Go to: API keys → Create new secret key
# 3. Copy key that looks like: sk-proj-...
# Note: Requires $5+ credit (free trial may not work)

OPENAI_API_KEY=sk-proj-...your_key_here
```

#### 4️⃣ NewsData.io API (News Feed - Required)

```bash
# 1. Sign up: https://newsdata.io/register
# 2. Go to: Dashboard → API Keys
# 3. Copy your API key (starts with 'pub_')
# Free tier: 50 requests/day

NEWSDATA_API_KEY=pub_...your_key_here
```

#### 5️⃣ Groq API (Optional - Faster LLM)

```bash
# 1. Visit: https://console.groq.com
# 2. Sign up with Google/GitHub
# 3. Go to: API keys
# 4. Create and copy your API key
# Free tier: 100k tokens/minute (very fast)

GROQ_API_KEY=gsk_...your_key_here
```

#### 6️⃣ SerpAPI (Optional - Web Search)

```bash
# 1. Visit: https://serpapi.com/users/sign_up
# 2. Create account
# 3. Go to: Dashboard → API key
# Free tier: 100 searches/month

SERPAPI_KEY=your_key_here
```

### 2. Environment Setup

Create `backend/.env` with your credentials:

```bash
# ===== DATABASE =====
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
MONGODB_DB=news_db
MONGODB_DB_NAME=bond_portfolio_db
DATABASE_NAME=news_db

# ===== REQUIRED API KEYS =====
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key_here
NEWSDATA_API_KEY=your_newsdata_api_key

# ===== OPTIONAL API KEYS =====
GROQ_API_KEY=your_groq_api_key
SERPAPI_KEY=your_serpapi_key
COMMODITY_API_KEY=your_commodity_api_key
PATHWAY_LICENSE_KEY=your_pathway_license_key

# ===== INFRASTRUCTURE =====
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_SASL_USERNAME=
KAFKA_SASL_PASSWORD=
REDIS_HOST=redis
REDIS_PORT=6379

# ===== API CONFIGURATION =====
API_HOST=0.0.0.0
API_PORT=8000
API_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ===== MCP SERVERS =====
PATHWAY_MCP_URL=http://localhost:8123/mcp/
MCP_URL=http://localhost:8123/mcp/
MCP_HOST=localhost
MCP_PORT=8127

# ===== LLM CONFIGURATION =====
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.0
OPENAI_BASE_URL=

# ===== FEATURE FLAGS =====
ENABLE_GUARDRAILS=false
RAG_ENABLED=true

# ===== FILE PATHS & DIRECTORIES =====
FOREX_CONFIG_PATH=backend/app/forex/configs/
PORTFOLIO_DB_PATH=files-mock/portfolios
CACHE_DIR=files-mock/cache
VECTOR_DB_PATH=vector_store

# ===== PIPELINE CONFIGURATION =====
SCRAPE_INTERVAL=300
BOND_STARTUP_DELAY=30
TEST_COMPANY=all
MAX_CONCURRENT_STRATEGIES=10
RATE_LIMIT_RPM=2000
```

### 3. Start the Platform

```bash
# Using the quick-start script (recommended)
./platform.sh start

# Or using docker-compose directly
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access Services

- **Frontend Dashboard**: http://localhost or http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Bond MCP Server**: http://localhost:8123
- **Forex MCP Server**: http://localhost:8127

### 5. Health Check

```bash
# Check all services
./platform.sh health

# Or manually
curl http://localhost:8000/health
curl http://localhost/
```

## 🔧 Environment Variables Reference

### Database Configuration

- **MONGODB_URI** - MongoDB connection string (Atlas or self-hosted)
- **MONGODB_DB** - News database name (default: news_db)
- **MONGODB_DB_NAME** - Bond portfolio database name (default: bond_portfolio_db)
- **DATABASE_NAME** - Alternative database name

### Required API Keys

- **OPENAI_API_KEY** - OpenAI API key for GPT-4o models ⭐
- **GEMINI_API_KEY** - Google Gemini API key for article summarization ⭐
- **NEWSDATA_API_KEY** - NewsData.io API key for news feed enrichment ⭐

### Optional API Keys

- **GROQ_API_KEY** - Groq LLM for faster inference (optional guardrails)
- **SERPAPI_KEY** - SerpAPI for web search in bond analysis
- **COMMODITY_API_KEY** - Commodity price data API
- **PATHWAY_LICENSE_KEY** - Pathway stream processing license

### Infrastructure & Messaging

- **KAFKA_BOOTSTRAP_SERVERS** - Kafka brokers (default: kafka:9092)
- **KAFKA_SECURITY_PROTOCOL** - Kafka auth protocol (default: PLAINTEXT)
- **KAFKA_SASL_USERNAME** - Kafka username (if auth enabled)
- **KAFKA_SASL_PASSWORD** - Kafka password (if auth enabled)
- **REDIS_HOST** - Redis cache server (default: redis)
- **REDIS_PORT** - Redis port (default: 6379)

### API & Server Configuration

- **API_HOST** - FastAPI bind address (default: 0.0.0.0)
- **API_PORT** - FastAPI port (default: 8000)
- **API_BASE_URL** - API base URL for clients (default: http://localhost:8000)
- **CORS_ORIGINS** - Comma-separated allowed CORS origins

### MCP Servers (Model Context Protocol)

- **PATHWAY_MCP_URL** - Bond/Pathway MCP server URL (default: http://localhost:8123/mcp/)
- **MCP_URL** - Alternative MCP server URL reference
- **MCP_HOST** - MCP server hostname (default: localhost)
- **MCP_PORT** - MCP server port (default: 8127)

### LLM Configuration

- **LLM_MODEL** - Default LLM model (default: gpt-4o-mini)
- **LLM_TEMPERATURE** - LLM temperature for sampling (default: 0.0)
- **OPENAI_BASE_URL** - Custom OpenAI base URL (optional)

### Feature Flags

- **ENABLE_GUARDRAILS** - Enable Groq-based content guardrails (default: false)
- **RAG_ENABLED** - Enable RAG for bond analysis (default: true)

### File Paths & Data Directories

- **FOREX_CONFIG_PATH** - Forex configuration directory
- **PORTFOLIO_DB_PATH** - Portfolio data directory
- **CACHE_DIR** - Cache directory for temporary data
- **VECTOR_DB_PATH** - Vector database location

### Pipeline Configuration

- **SCRAPE_INTERVAL** - News scraping interval in seconds (default: 300)
- **BOND_STARTUP_DELAY** - Delay before bond pipeline starts (seconds)
- **TEST_COMPANY** - Test company identifier (default: all)
- **MAX_CONCURRENT_STRATEGIES** - Max concurrent processing strategies
- **RATE_LIMIT_RPM** - Rate limit for API calls (default: 2000/min)

## 📚 Documentation

- **[Complete Docker Deployment Guide](DOCKER_DEPLOYMENT.md)** - Detailed setup, troubleshooting, and production deployment
- **[Bonds API Documentation](docs/BONDS_API.md)** - Bond analysis endpoints
- **[Cashflow & Forex](docs/CASHFLOW+FOREX.md)** - Forex trading features
- **[Orchestrator Components](docs/ORCHESTRATOR_COMPONENTS.md)** - System architecture

## 🛠️ Management Commands

The `platform.sh` script provides easy management:

```bash
./platform.sh start          # Start all services
./platform.sh start-core     # Start core services only
./platform.sh stop           # Stop all services
./platform.sh status         # Show service status
./platform.sh logs [service] # View logs
./platform.sh health         # Check service health
./platform.sh rebuild <svc>  # Rebuild specific service
./platform.sh backup         # Backup important data
```

## 🎯 Service Overview

### Frontend Services

- **frontend** - React/Vite UI with Nginx

### API & MCP Servers

- **api** - FastAPI backend (Port 8000)
- **bond-mcp-server** - Bond analysis MCP (Port 8123)
- **forex-mcp-server** - Forex trading MCP (Port 8127)

### Data Pipelines

- **bond-pipeline** - Bond data collection and forecasting
- **news-scraper** - News metadata extraction
- **enrichment-pipeline** - Content fetching and sentiment
- **llm-worker** - AI summarization and analysis

### Infrastructure

- **kafka** - Message streaming (9092, 9093)
- **zookeeper** - Kafka coordination (2181)
- **redis** - Caching and deduplication (6379)

## 🔧 Development

### Frontend Development

cd upgraded-octo-spork

# Configure environment

cat > backend/.env << EOF
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DB=news_db
MONGODB_CONFIG_DB=config_db
GEMINI_API_KEY=your_gemini_api_key_here
EOF

# Start services

docker-compose up -d

# Initialize search config

docker exec -it news-scraper python /app/setup_search_config.py

# To initialize MCP server

cd backend/app/forex
python mcp_server.py

# Verify - API should respond

curl http://localhost:8000/health
curl http://localhost:8000/api/news/stats

````

**What `docker-compose up -d` starts:**
- ✅ **Infrastructure**: Kafka, Zookeeper, Redis
- ✅ **News Pipeline**: news-scraper → enrichment-pipeline → llm-worker
- ✅ **FastAPI Backend**: REST API server on port 8000
- ✅ **All networking**: Internal docker network with proper service discovery

**Access Points:**
- **FastAPI**: http://localhost:8000/docs (Interactive API docs)
- **News API**: http://localhost:8000/api/news/* (Articles, companies, stats)
- **Pathway Monitoring**: http://localhost:8080/metrics (Pipeline metrics)
- **MongoDB**: MongoDB Atlas (remote)
- **Redis**: localhost:6379

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

## 📊 API Examples

### Get Summarized Articles

```bash
# All articles
GET /api/news/summarized?limit=10

# Filter by company
GET /api/news/summarized?company=tcs&limit=5

# Filter by sentiment
GET /api/news/summarized?company=itc&sentiment=negative

# Date range
GET /api/news/summarized?start_date=2024-12-01&end_date=2024-12-02
````

### Get Companies

```bash
GET /api/news/companies
```

### Update Search Config

```bash
PUT /api/news/config
{
  "company_code": "tcs",
  "theme": "regulatory",
  "query": "(\"TCS\" OR \"Tata Consultancy\") AND (regulation OR compliance) -job"
}
```

### Get Statistics

```bash
GET /api/news/stats
```

See full API documentation at http://localhost:8000/docs

## 📁 Project Structure

```
.
├── backend/
│   ├── app/                    # FastAPI application
│   │   ├── routes/
│   │   │   ├── chats.py
│   │   │   ├── versions.py
│   │   │   └── news.py         # News API ✨
│   │   └── models/
│   │       └── news.py         # News models ✨
│   │
│   ├── services/               # Microservices
│   │   ├── news-scraper/       # Layer 1: Scraping
│   │   ├── enrichment-pipeline/   # Layer 2: Processing
│   │   └── llm-worker/         # Layer 3: Summarization
│   │
│   ├── main.py                 # FastAPI entry point
│   └── Dockerfile              # FastAPI container ✨
│
├── frontend/                   # React frontend
├── docker-compose.yml          # All services ✨
└── README.md
```

## 🔧 Configuration

### Quick Environment Setup Guide

#### 1️⃣ MongoDB Atlas (Database)

```bash
# Step 1: Create free account at https://www.mongodb.com/cloud/atlas
# Step 2: Create a cluster (M0 free tier works perfectly)
# Step 3: Create database user with read/write permissions
# Step 4: Whitelist your IP (0.0.0.0/0 for development)
# Step 5: Get connection string from "Connect" button
# Example format:
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname?retryWrites=true&w=majority
```

#### 2️⃣ Google Gemini (Article Summarization)

```bash
# Step 1: Visit https://aistudio.google.com/app/apikeys
# Step 2: Click "Create API Key"
# Step 3: Copy the key and add to .env
GEMINI_API_KEY=AIzaSy...your_key_here
```

#### 3️⃣ OpenAI (GPT Models)

```bash
# Step 1: Sign up at https://platform.openai.com
# Step 2: Go to API Keys → Create New Secret Key
# Step 3: Add to .env
OPENAI_API_KEY=sk-...your_key_here
```

#### 4️⃣ NewsData.io (News Feed)

```bash
# Step 1: Sign up at https://newsdata.io
# Step 2: Go to Dashboard → API Keys
# Step 3: Copy and add to .env
NEWSDATA_API_KEY=pub_...your_key_here
```

#### 5️⃣ Groq (Optional - Faster LLM)

```bash
# Step 1: Visit https://console.groq.com
# Step 2: Create API Key
# Step 3: Add to .env (optional)
GROQ_API_KEY=gsk_...your_key_here
```

#### 6️⃣ SerpAPI (Optional - Web Search)

```bash
# Step 1: Visit https://serpapi.com
# Step 2: Create API Key
# Step 3: Add to .env (optional)
SERPAPI_KEY=your_key_here
```

### Environment Variables

### Adding Companies

```bash
# Via API
POST /api/news/config/company
{
  "company_code": "reliance",
  "aliases": ["Reliance", "Reliance Industries", "RIL"]
}

# Via script
docker exec -it news-scraper python -c "
from companies import SEARCH_CONFIG
# Edit SEARCH_CONFIG
# Then run setup_search_config.py
"
```

## 📈 Monitoring

### Service Health

```bash
# API health
curl http://localhost:8000/health

# Pathway metrics
curl http://localhost:8080/metrics

# Service status
docker-compose ps

# Logs
docker-compose logs -f
```

### MongoDB Queries

```bash
# Connect to Atlas with mongosh
mongosh "$MONGODB_URI"

# Or use the API
curl http://localhost:8000/api/news/stats

# Query scripts (requires mongosh + MONGODB_URI env var)
MONGODB_URI='mongodb+srv://admin:admin@cluster0.xfoccu0.mongodb.net/?appName=Cluster0' ./scripts/query-news.sh stats
```

## 🧪 Development

```bash
# Start only infrastructure
docker-compose up -d kafka redis

# Run FastAPI locally
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Run specific service
docker-compose up -d news-scraper

# View logs
docker-compose logs -f news-scraper
```

## 🛠️ Troubleshooting

### Missing Environment Variables Error

If you see errors like `OPENAI_API_KEY not set` or `GEMINI_API_KEY missing`:

```bash
# 1. Verify your .env file exists and is in the right location
ls -la backend/.env

# 2. Check all required variables are set
cat backend/.env | grep -E "OPENAI_API_KEY|GEMINI_API_KEY|NEWSDATA_API_KEY|MONGODB_URI"

# 3. Load environment variables (for local testing)
source backend/.env
echo $OPENAI_API_KEY  # Should print your key

# 4. Restart services after updating .env
docker-compose down
docker-compose up -d

# 5. Check logs for errors
docker-compose logs api
docker-compose logs news-scraper
```

### Required vs Optional Variables

**Must be set (or services won't start):**

- ✅ `MONGODB_URI` - Database connection
- ✅ `OPENAI_API_KEY` - GPT model for orchestration
- ✅ `GEMINI_API_KEY` - Article summarization
- ✅ `NEWSDATA_API_KEY` - News feed data

**Optional (but recommended):**

- 📌 `GROQ_API_KEY` - Faster LLM inference (fallback if OpenAI fails)
- 📌 `SERPAPI_KEY` - Web search for bonds analysis

**Auto-configured (no setup needed):**

- ✨ `KAFKA_BOOTSTRAP_SERVERS` - Set to `kafka:9092` in Docker
- ✨ `REDIS_HOST` - Set to `redis` in Docker
- ✨ `API_PORT` - Defaults to 8000

### No Articles Appearing?

```bash
# Check scraper logs
docker-compose logs -f news-scraper

# Verify config loaded via API
curl http://localhost:8000/api/news/companies
```

### Pipeline not processing?

```bash
# Check Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Check messages
docker exec -it kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic raw-news-feed \
    --max-messages 5
```

### Can't connect to MongoDB Atlas?

```bash
# Test connection string
mongosh "$MONGODB_URI" --eval "db.adminCommand('ping')"

# Check API logs
docker logs api -f
```

## 📝 Roadmap

- [x] News scraping with deduplication
- [x] Sentiment analysis (FinBERT)
- [x] LLM summarization (Gemini)
- [x] REST API with filters
- [x] Story clustering
- [ ] Twitter intelligence pipeline
- [ ] Compliance document RAG
- [ ] Stock price analysis
- [ ] Real-time alerts
- [ ] Email/Slack notifications

## 📚 Documentation

- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Backend README](backend/README.md) - Backend architecture and services

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🆘 Support

- **Documentation**: See docs above
- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/upgraded-octo-spork/issues)
- **Email**: your-email@example.com

## 🙏 Acknowledgments

- **Pathway**: Stream processing framework
- **FinBERT**: Financial sentiment analysis
- **Gemini**: LLM summarization
- **FastAPI**: Modern Python web framework

---

## ❓ FAQ

### Does docker-compose start FastAPI too?

**Yes!** Running `docker-compose up -d` starts:

- Infrastructure (Kafka, Redis)
- News pipeline (scraper, enrichment-pipeline, llm-worker)
- **FastAPI backend** on port 8000

All services are in one `docker-compose.yml`.

### How do I set up MongoDB Atlas?

1. Create free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Create a cluster (M0 free tier works)
3. Add database user with read/write permissions
4. Whitelist your IP address (or 0.0.0.0/0 for testing)
5. Get connection string and add to `backend/.env`

### Can I run FastAPI separately?

Yes, for development:

```bash
# Start only infrastructure
docker-compose up -d kafka redis mongodb

# Run FastAPI locally
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### How do I scale this?

- **Horizontal**: Run multiple worker containers (llm-worker, enrichment-pipeline)
- **Vertical**: Increase VM resources (more RAM/CPU)
- **Database**: MongoDB Atlas auto-scales

```bash
# Scale LLM workers
docker-compose up -d --scale llm-worker=3
```

---
