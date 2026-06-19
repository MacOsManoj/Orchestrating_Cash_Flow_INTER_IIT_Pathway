#!/bin/bash
# MongoDB Setup Script for macOS

set -e

echo " MongoDB Setup Script"
echo "========================"
echo ""

# Check if MongoDB is already running
if mongosh --eval "db.version()" &>/dev/null; then
    echo " MongoDB is already running!"
    exit 0
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo " Homebrew is not installed."
    echo "Please install Homebrew first: https://brew.sh"
    echo ""
    echo "Or use MongoDB Atlas (cloud) - see QUICKSTART_MONGODB.md"
    exit 1
fi

echo " Installing MongoDB Community Edition..."
brew tap mongodb/brew
brew install mongodb-community

echo ""
echo " Starting MongoDB service..."
brew services start mongodb-community

echo ""
echo "Waiting for MongoDB to start..."
sleep 5

# Test connection
if mongosh --eval "db.version()" &>/dev/null; then
    echo " MongoDB is running successfully!"
    echo ""
    echo " Next steps:"
    echo "1. Add to your .env file:"
    echo "   MONGODB_URI=mongodb://localhost:27017/"
    echo "   MONGODB_DB_NAME=bond_portfolio_db"
    echo ""
    echo "2. Load mock data:"
    echo "   python scripts/load_portfolios_to_mongodb.py"
    exit 0
else
    echo "  MongoDB may still be starting. Please wait a moment and try:"
    echo "   mongosh --eval 'db.version()'"
    exit 1
fi

