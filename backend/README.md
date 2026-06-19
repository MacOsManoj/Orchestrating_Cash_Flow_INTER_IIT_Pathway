# News Processing System - Backend

Production-ready real-time news processing pipeline with streaming, sentiment analysis, and LLM summarization.

## 📁 Directory Structure

```
backend/
├── config/                      # Configuration files
│   └── docker-compose.yml       # Docker orchestration
│
├── services/                    # Microservices
│   ├── news-scraper/           # Layer 1: Lightweight metadata scraper
│   ├── enrichment-pipeline/       # Layer 3: Streaming enrichment pipeline
│   └── llm-worker/             # Layer 4: AI summarization worker
│
├── scripts/                     # Management scripts
│   ├── setup.sh                # Initial setup
│   ├── start.sh                # Start all services
│   ├── stop.sh                 # Stop all services
│   ├── logs.sh                 # View logs
│   └── health-check.sh         # Health check
│
├── docs/                        # Documentation
│   └── README.md               # Comprehensive docs
│
├── data-collection/            # Legacy scraper (for reference)
│
└── .env.example                # Environment template
```

## 🚀 Quick Start

```bash
# 1. Setup infrastructure
./scripts/setup.sh

# 2. Configure API key
cp .env.example .env
nano .env  # Add GEMINI_API_KEY

# 3. Start services
./scripts/start.sh

# 4. Check health
./scripts/health-check.sh
```

## 📚 Full Documentation

See [docs/README.md](docs/README.md) for:
- Complete architecture overview
- Service details and configuration
- Monitoring and debugging
- Scaling and performance tuning
- Troubleshooting guide

## 🔧 Common Commands

```bash
# View logs
./scripts/logs.sh all                    # All services
./scripts/logs.sh news-scraper          # Specific service

# Stop services
./scripts/stop.sh

# Scale workers
cd config && docker compose up -d --scale llm-worker=3

# Clean restart
cd config && docker compose down -v && cd .. && ./scripts/setup.sh
```

## 📊 Service URLs

- **Pathway Monitoring**: http://localhost:8080
- **MongoDB**: mongodb://localhost:27017
- **Redis**: redis://localhost:6379
- **Kafka**: localhost:9093

## 🏗️ Architecture

```
News Sources → Scraper → Kafka → Pathway → LLM Worker → Storage
               (Dedup)   (Broker) (Enrich)  (Summarize)  (MongoDB)
```

**Key Features:**
- ✅ 3-layer deduplication (Bloom Filter + Redis + MongoDB)
- ✅ Real FinBERT sentiment analysis
- ✅ Google Gemini API integration
- ✅ Horizontally scalable workers
- ✅ Real-time streaming with Pathway
- ✅ Complete Docker orchestration
