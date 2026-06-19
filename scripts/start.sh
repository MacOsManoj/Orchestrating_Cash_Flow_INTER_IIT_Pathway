#!/bin/bash

# ========================================
# Start Script for News Processing System
# ========================================

set -e

echo "========================================="
echo "News Processing System - Starting"
echo "========================================="

# Load environment variables from backend/.env
if [ -f backend/.env ]; then
    export $(cat backend/.env | grep -v '^#' | xargs)
    echo "✅ Loaded environment from backend/.env"
elif [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded environment from .env"
fi

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo "⚠️  WARNING: GEMINI_API_KEY not set in .env file"
    echo "The LLM worker will not function properly without a valid API key."
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Starting all services..."
docker compose -f docker-compose.yml up -d

echo ""
echo "Waiting for services to initialize..."
sleep 10

echo ""
echo "========================================="
echo "✓ All Services Started!"
echo "========================================="
echo ""
echo "Running services:"
docker compose -f docker-compose.yml ps

echo ""
echo "Service URLs:"
echo "  - FastAPI: http://localhost:8000/docs"
echo "  - Pathway Monitoring: http://localhost:8080"
echo "  - Kafka: localhost:9093"
echo "  - Redis: localhost:6379"
echo "  - MongoDB: Atlas (remote)"
echo ""
echo "To view logs:"
echo "  - All services:     docker compose -f docker-compose.yml logs -f"
echo "  - Scraper:          docker compose -f docker-compose.yml logs -f news-scraper"
echo "  - Enrichment:       docker compose -f docker-compose.yml logs -f enrichment-pipeline"
echo "  - LLM Worker:       docker compose -f docker-compose.yml logs -f llm-worker"
echo ""
echo "To stop services:"
echo "  ./scripts/stop.sh"
echo ""
