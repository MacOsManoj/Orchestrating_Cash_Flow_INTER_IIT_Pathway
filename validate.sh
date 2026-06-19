#!/bin/bash

# Pre-flight Validation Script
# Checks if the platform is ready to start

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        return 0
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

ERRORS=0

print_header "Docker Environment Validation"

# Check Docker
docker --version > /dev/null 2>&1
print_check $? "Docker is installed" || ((ERRORS++))

# Check Docker Compose
docker-compose --version > /dev/null 2>&1
print_check $? "Docker Compose is installed" || ((ERRORS++))

# Check Docker daemon
docker ps > /dev/null 2>&1
print_check $? "Docker daemon is running" || ((ERRORS++))

print_header "File Structure Validation"

# Check required directories
for dir in backend frontend backend/services; do
    [ -d "$dir" ]
    print_check $? "Directory exists: $dir" || ((ERRORS++))
done

# Check required files
files=(
    "docker-compose.yml"
    "backend/Dockerfile"
    "frontend/Dockerfile"
    "frontend/nginx.conf"
    "backend/services/forex/Dockerfile"
    "backend/services/forex/requirements.txt"
)

for file in "${files[@]}"; do
    [ -f "$file" ]
    print_check $? "File exists: $file" || ((ERRORS++))
done

print_header "Environment Configuration"

# Check backend .env
if [ -f "backend/.env" ]; then
    print_check 0 "backend/.env exists"
    
    # Check for required variables
    required_vars=("MONGODB_URI" "PATHWAY_LICENSE_KEY")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" backend/.env && ! grep -q "^${var}=your_" backend/.env; then
            print_check 0 "$var is configured"
        else
            print_check 1 "$var needs to be set in backend/.env"
            ((ERRORS++))
        fi
    done
else
    print_check 1 "backend/.env is missing - create from template"
    ((ERRORS++))
fi

# Check frontend .env.production
if [ -f "frontend/.env.production" ]; then
    print_check 0 "frontend/.env.production exists"
else
    print_check 1 "frontend/.env.production is missing"
    ((ERRORS++))
fi

print_header "Port Availability"

# Check if ports are available
ports=(80 3000 8000 8123 8127 9092 6379 2181)
for port in "${ports[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_check 1 "Port $port is already in use"
        ((ERRORS++))
    else
        print_check 0 "Port $port is available"
    fi
done

print_header "Docker Network"

# Check if network exists
if docker network ls | grep -q intelligence_network; then
    echo -e "${YELLOW}⚠️  Network 'intelligence_network' already exists (this is ok)${NC}"
else
    print_check 0 "Network ready to be created"
fi

print_header "System Resources"

# Check available memory (Linux only)
if [ -f /proc/meminfo ]; then
    total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    total_mem_gb=$((total_mem / 1024 / 1024))
    if [ $total_mem_gb -ge 16 ]; then
        print_check 0 "Memory: ${total_mem_gb}GB (recommended: 16GB+)"
    else
        echo -e "${YELLOW}⚠️  Memory: ${total_mem_gb}GB (recommended: 16GB+)${NC}"
    fi
fi

# Check available disk space
available_space=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ $available_space -ge 20 ]; then
    print_check 0 "Disk space: ${available_space}GB available (recommended: 20GB+)"
else
    echo -e "${YELLOW}⚠️  Disk space: ${available_space}GB (recommended: 20GB+)${NC}"
fi

print_header "Validation Summary"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to start the platform.${NC}"
    echo ""
    echo "Run: ./platform.sh start"
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS error(s). Please fix them before starting.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  1. Create backend/.env from template"
    echo "  2. Configure MONGODB_URI and PATHWAY_LICENSE_KEY"
    echo "  3. Free up required ports (stop conflicting services)"
    echo "  4. Install Docker and Docker Compose if missing"
    exit 1
fi
