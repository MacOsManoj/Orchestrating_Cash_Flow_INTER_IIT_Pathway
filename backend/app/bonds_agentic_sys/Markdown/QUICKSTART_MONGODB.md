# Quick Start: MongoDB Setup

MongoDB is not currently installed. You have two options:

## Option 1: Install MongoDB Locally (Recommended for Development)

### macOS (using Homebrew)

```bash
# Install MongoDB Community Edition
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB service
brew services start mongodb-community

# Verify it's running
mongosh --eval "db.version()"
```

### Alternative: Run MongoDB in Docker

If you have Docker installed:

```bash
# Run MongoDB in a Docker container
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:latest

# Verify it's running
docker ps | grep mongodb
```

## Option 2: Use MongoDB Atlas (Cloud - No Installation Required)

1. **Sign up for free**: https://www.mongodb.com/cloud/atlas/register
2. **Create a free cluster** (M0 tier is free forever)
3. **Create a database user** (Database Access → Add New User)
4. **Whitelist your IP** (Network Access → Add IP Address → Add Current IP Address)
5. **Get connection string**:
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Copy the connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)
6. **Update your `.env` file**:
   ```bash
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
   MONGODB_DB_NAME=bond_portfolio_db
   ```

## After Setup

Once MongoDB is running (either locally or Atlas), run:

```bash
# Test connection
python scripts/test_mongodb_connection.py

# Load mock data
python scripts/load_portfolios_to_mongodb.py
```

## Quick Install Script (macOS)

Run this to install MongoDB locally:

```bash
# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install MongoDB
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
brew services start mongodb-community

# Wait a moment for MongoDB to start
sleep 3

# Test connection
mongosh --eval "db.version()" && echo "✅ MongoDB is running!" || echo "❌ MongoDB failed to start"
```

