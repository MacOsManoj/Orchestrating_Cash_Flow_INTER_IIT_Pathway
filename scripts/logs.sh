#!/bin/bash

# ========================================
# View Logs for News Processing System
# ========================================

SERVICE=${1:-all}

echo "========================================="
echo "Viewing logs for: $SERVICE"
echo "========================================="
echo ""

if [ "$SERVICE" = "all" ]; then
    docker compose -f docker-compose.yml logs -f --tail=100
else
    docker compose -f docker-compose.yml logs -f --tail=100 $SERVICE
fi
