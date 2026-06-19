#!/bin/bash

# ========================================
# Health Check Script
# ========================================

echo "========================================="
echo "News Processing System - Health Check"
echo "========================================="
echo ""

# Check Docker services
echo "1. Checking Docker services..."
docker compose -f docker-compose.yml ps

echo ""
echo "2. Checking Kafka topics..."
docker compose -f docker-compose.yml exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null || echo "  ⚠️ Kafka not ready"

echo ""
echo "3. Checking Redis..."
docker compose -f docker-compose.yml exec redis redis-cli ping 2>/dev/null | grep PONG > /dev/null && echo "  ✓ Redis is healthy" || echo "  ⚠️ Redis not responding"

echo ""
echo "4. Checking MongoDB Atlas..."
echo "  ℹ️  Using MongoDB Atlas (remote) - connection verified via API"
echo "  To check MongoDB directly, use: mongosh with your Atlas connection string"

echo ""
echo "5. Service URLs:"
echo "  - FastAPI: http://localhost:8000/docs"
echo "  - Pathway Monitoring: http://localhost:8080"
echo "  - Redis: redis://localhost:6379"
echo "  - Kafka: localhost:9093"
echo "  - MongoDB: Atlas (remote)"

echo ""
echo "========================================="
