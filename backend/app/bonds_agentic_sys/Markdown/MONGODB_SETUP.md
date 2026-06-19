# MongoDB Setup for Portfolio Manager

This guide explains how to set up MongoDB for the Portfolio Manager system.

## Prerequisites

1. **MongoDB Installation**
   - Install MongoDB locally or use MongoDB Atlas (cloud)
   - For local installation: https://www.mongodb.com/try/download/community
   - For MongoDB Atlas: https://www.mongodb.com/cloud/atlas

2. **Python Dependencies**
   - `pymongo>=4.6.0` (already added to requirements.txt)

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# MongoDB Connection String
# For local MongoDB:
MONGODB_URI=mongodb://localhost:27017/

# For MongoDB Atlas (cloud):
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Database Name (optional, defaults to 'bond_portfolio_db')
MONGODB_DB_NAME=bond_portfolio_db
```

### Local MongoDB Setup

1. **Install MongoDB** (if not already installed):
   ```bash
   # macOS (using Homebrew)
   brew tap mongodb/brew
   brew install mongodb-community
   
   # Start MongoDB service
   brew services start mongodb-community
   ```

2. **Verify MongoDB is running**:
   ```bash
   mongosh
   # or
   mongo
   ```

### MongoDB Atlas Setup (Cloud)

1. Create a free account at https://www.mongodb.com/cloud/atlas
2. Create a new cluster
3. Create a database user
4. Whitelist your IP address
5. Get your connection string and add it to `.env`

## Loading Mock Data

### Load Portfolios from JSON Files

Run the data loading script:

```bash
cd bond-pipeline
python scripts/load_portfolios_to_mongodb.py
```

Options:
- `--portfolios-dir`: Specify directory with portfolio JSON files (default: `files-mock/portfolios`)
- `--clear`: Clear existing portfolios before loading
- `--additional`: Also load additional programmatically created mock portfolios

Example:
```bash
# Load portfolios and clear existing data
python scripts/load_portfolios_to_mongodb.py --clear

# Load with additional mock portfolios
python scripts/load_portfolios_to_mongodb.py --additional
```

### Verify Data Load

You can verify the data was loaded by:

1. **Using MongoDB Shell**:
   ```bash
   mongosh
   use bond_portfolio_db
   db.portfolios.find().pretty()
   ```

2. **Using Python**:
   ```python
   from utils.mongodb_client import get_mongodb_client
   
   client = get_mongodb_client()
   collection = client.portfolios_collection
   count = collection.count_documents({})
   print(f"Total portfolios: {count}")
   ```

## Usage in Code

The Portfolio Manager automatically uses MongoDB if available, with fallback to file-based storage:

```python
from agents.portfolio_manager import create_portfolio_manager

# Create portfolio manager (uses MongoDB by default)
manager = create_portfolio_manager(use_mongodb=True)

# Get portfolio
portfolio = manager.get_portfolio("SAMPLE_USER_001")

# Save portfolio
manager.save_portfolio(portfolio, "SAMPLE_USER_001")
```

## Database Schema

The `portfolios` collection stores documents with the following structure:

```json
{
  "user_id": "SAMPLE_USER_001",
  "portfolio_id": "PF_001",
  "name": "Portfolio SAMPLE_USER_001",
  "total_value": 201500.0,
  "cash": 25000.0,
  "duration": 4.25,
  "ytm": 7.15,
  "sector_exposures": {
    "Sovereign": 0.5,
    "Private_Financial": 0.25,
    "PSU_Energy": 0.15
  },
  "rating_exposures": {
    "AAA": 1.0
  },
  "positions": [
    {
      "isin": "INE001A01036",
      "name": "HDFC Bank 7.50% 2025",
      "quantity": 500.0,
      "avg_cost": 101.2,
      "current_price": 101.5,
      "market_value": 50750.0,
      "weight": 0.25,
      "unrealized_pnl": 150.0
    }
  ],
  "last_updated": "2025-01-28T10:00:00Z"
}
```

## Indexes

For better performance, you can create indexes:

```javascript
// In MongoDB shell
use bond_portfolio_db

// Index on user_id for fast lookups
db.portfolios.createIndex({ "user_id": 1 })

// Index on portfolio_id
db.portfolios.createIndex({ "portfolio_id": 1 })

// Index on bank_id
db.portfolios.createIndex({ "bank_id": 1 })
```

## Troubleshooting

### Connection Issues

1. **Check MongoDB is running**:
   ```bash
   # Local MongoDB
   brew services list  # macOS
   sudo systemctl status mongod  # Linux
   ```

2. **Check connection string**:
   - Verify `MONGODB_URI` in `.env` is correct
   - For Atlas, ensure IP is whitelisted

3. **Test connection**:
   ```python
   from utils.mongodb_client import get_mongodb_client
   
   client = get_mongodb_client()
   if client.is_connected():
       print("✓ Connected to MongoDB")
   else:
       print("✗ MongoDB connection failed")
   ```

### Fallback to File Storage

If MongoDB is not available, the system automatically falls back to file-based storage in `files-mock/portfolios/`. You'll see a warning message:

```
⚠️  Portfolio Manager: MongoDB not connected, using file-based storage
```

## Migration from File-Based Storage

If you have existing portfolios in JSON files and want to migrate to MongoDB:

1. Ensure MongoDB is running and configured
2. Run the load script:
   ```bash
   python scripts/load_portfolios_to_mongodb.py
   ```
3. The system will automatically use MongoDB for new operations

## Production Considerations

For production deployments:

1. **Use MongoDB Atlas** or a managed MongoDB service
2. **Enable authentication**:
   ```bash
   MONGODB_URI=mongodb://username:password@host:port/database
   ```
3. **Use connection pooling** (already handled by pymongo)
4. **Set up backups** and monitoring
5. **Create appropriate indexes** for your query patterns
6. **Use read/write concerns** for data consistency

