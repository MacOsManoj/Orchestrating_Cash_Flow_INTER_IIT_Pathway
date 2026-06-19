#!/bin/bash

# Financial Intelligence Platform - Quick Start Script
# This script helps manage the complete Docker infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    echo -e "${2}${1}${NC}"
}

# Print section header
print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check if .env exists
check_env() {
    if [ ! -f "backend/.env" ]; then
        print_msg "⚠️  Warning: backend/.env not found!" "$YELLOW"
        print_msg "Creating template .env file..." "$YELLOW"
        cat > backend/.env << 'EOF'
# MongoDB (External - Atlas/GCP)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname

# API Keys
PATHWAY_LICENSE_KEY=your_pathway_license_key
NEWSDATA_API_KEY=your_newsdata_api_key

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key

# Optional
BOND_STARTUP_DELAY=30
EOF
        print_msg "✅ Template .env created at backend/.env" "$GREEN"
        print_msg "⚠️  Please edit backend/.env with your actual credentials!" "$RED"
        exit 1
    fi
}

# Start all services
start_all() {
    print_header "🚀 Starting All Services"
    check_env
    docker-compose up -d
    print_msg "✅ All services started!" "$GREEN"
    show_urls
}

# Start infrastructure only
start_infra() {
    print_header "🔧 Starting Infrastructure"
    docker-compose up -d zookeeper kafka redis kafka-init
    print_msg "✅ Infrastructure started!" "$GREEN"
}

# Start core services (API + MCP)
start_core() {
    print_header "🎯 Starting Core Services"
    check_env
    start_infra
    sleep 5
    docker-compose up -d bond-pipeline bond-mcp-server forex-mcp-server api frontend
    print_msg "✅ Core services started!" "$GREEN"
    show_urls
}

# Start news pipeline
start_news() {
    print_header "📰 Starting News Pipeline"
    check_env
    start_infra
    sleep 5
    docker-compose up -d news-scraper enrichment-pipeline llm-worker
    print_msg "✅ News pipeline started!" "$GREEN"
}

# Stop all services
stop_all() {
    print_header "🛑 Stopping All Services"
    docker-compose down
    print_msg "✅ All services stopped!" "$GREEN"
}

# Stop and remove volumes
clean_all() {
    print_header "🧹 Cleaning Up (including volumes)"
    read -p "This will DELETE all data volumes. Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        print_msg "✅ All services and volumes removed!" "$GREEN"
    else
        print_msg "Cancelled." "$YELLOW"
    fi
}

# Show service status
status() {
    print_header "📊 Service Status"
    docker-compose ps
}

# Show logs
logs() {
    if [ -z "$1" ]; then
        print_header "📜 Viewing All Logs (Ctrl+C to exit)"
        docker-compose logs -f
    else
        print_header "📜 Viewing Logs for: $1"
        docker-compose logs -f "$1"
    fi
}

# Show service URLs
show_urls() {
    print_header "🌐 Service URLs"
    echo -e "${GREEN}Frontend:${NC}     http://localhost"
    echo -e "${GREEN}              http://localhost:3000${NC}"
    echo -e "${GREEN}API Docs:${NC}     http://localhost:8000/docs"
    echo -e "${GREEN}Bond MCP:${NC}     http://localhost:8123"
    echo -e "${GREEN}Forex MCP:${NC}    http://localhost:8127"
    echo -e "${GREEN}Kafka:${NC}        localhost:9092"
    echo -e "${GREEN}Redis:${NC}        localhost:6379"
}

# Health check
health() {
    print_header "🏥 Health Check"
    
    services=("frontend:http://localhost" "api:http://localhost:8000/health" "bond-mcp-server:http://localhost:8123" "forex-mcp-server:http://localhost:8127/mcp/")
    
    for service_url in "${services[@]}"; do
        IFS=':' read -r service url <<< "$service_url"
        url="${url}:${service_url##*:}"
        
        if curl -sf "$url" > /dev/null 2>&1; then
            print_msg "✅ $service: OK" "$GREEN"
        else
            print_msg "❌ $service: DOWN" "$RED"
        fi
    done
}

# Rebuild specific service
rebuild() {
    if [ -z "$1" ]; then
        print_msg "Usage: $0 rebuild <service_name>" "$RED"
        print_msg "Example: $0 rebuild frontend" "$YELLOW"
        exit 1
    fi
    
    print_header "🔨 Rebuilding $1"
    docker-compose build --no-cache "$1"
    docker-compose up -d "$1"
    print_msg "✅ $1 rebuilt and restarted!" "$GREEN"
}

# Show resource usage
resources() {
    print_header "💾 Resource Usage"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Backup volumes
backup() {
    print_header "💾 Backing up volumes"
    BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    volumes=("bonds_forecasts" "bonds_cache" "forex_data")
    
    for vol in "${volumes[@]}"; do
        print_msg "Backing up $vol..." "$BLUE"
        docker run --rm \
            -v "upgraded-octo-spork_${vol}:/data" \
            -v "$(pwd)/${BACKUP_DIR}:/backup" \
            alpine tar czf "/backup/${vol}.tar.gz" -C /data .
        print_msg "✅ $vol backed up" "$GREEN"
    done
    
    print_msg "✅ All backups saved to: $BACKUP_DIR" "$GREEN"
}

# Show help
show_help() {
    cat << EOF
🚀 Financial Intelligence Platform - Quick Start

Usage: $0 [command] [options]

Commands:
  start          Start all services
  start-core     Start core services (API, MCP, Frontend)
  start-infra    Start infrastructure only (Kafka, Redis)
  start-news     Start news pipeline
  stop           Stop all services
  clean          Stop and remove all volumes (DELETES DATA!)
  
  status         Show service status
  logs [service] Show logs (all or specific service)
  health         Check health of all services
  urls           Show service URLs
  
  rebuild <svc>  Rebuild specific service
  resources      Show resource usage
  backup         Backup important volumes
  
  help           Show this help message

Examples:
  $0 start                 # Start everything
  $0 start-core            # Start core services only
  $0 logs api              # View API logs
  $0 rebuild frontend      # Rebuild frontend
  $0 health                # Check all services

Services:
  - frontend            React/Vite UI
  - api                 FastAPI Backend
  - bond-mcp-server     Bond Analysis MCP
  - forex-mcp-server    Forex Trading MCP
  - bond-pipeline       Bond Data Pipeline
  - news-scraper        News Scraper
  - enrichment-pipeline Content Enrichment
  - llm-worker          LLM Summarization
  - kafka               Message Broker
  - redis               Cache Store

EOF
}

# Main command handler
case "${1:-help}" in
    start)
        start_all
        ;;
    start-core)
        start_core
        ;;
    start-infra)
        start_infra
        ;;
    start-news)
        start_news
        ;;
    stop)
        stop_all
        ;;
    clean)
        clean_all
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    health)
        health
        ;;
    urls)
        show_urls
        ;;
    rebuild)
        rebuild "$2"
        ;;
    resources)
        resources
        ;;
    backup)
        backup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_msg "Unknown command: $1" "$RED"
        echo ""
        show_help
        exit 1
        ;;
esac
