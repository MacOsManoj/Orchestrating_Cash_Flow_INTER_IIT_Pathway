#!/bin/bash

# ========================================
# Stop Script for News Processing System
# ========================================

set -e

echo "========================================="
echo "News Processing System - Stopping"
echo "========================================="

echo ""
echo "Stopping all services..."
docker compose -f docker-compose.yml down

echo ""
echo "========================================="
echo "✓ All Services Stopped!"
echo "========================================="
echo ""
echo "To start services again:"
echo "  ./scripts/start.sh"
echo ""
echo "To remove all data (volumes):"
echo "  docker compose -f docker-compose.yml down -v"
echo ""
