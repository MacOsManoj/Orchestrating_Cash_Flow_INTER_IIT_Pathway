from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


class Database:
    """
    Database connection manager
    """

    client: AsyncIOMotorClient = None


# Global database instance
db = Database()


async def connect_to_mongo():
    """
    Connect to MongoDB on application startup
    """
    print(f"Connecting to MongoDB at {settings.MONGODB_URI}")
    db.client = AsyncIOMotorClient(settings.MONGODB_URI)

    # Test connection
    try:
        await db.client.admin.command("ping")
        print("✅ Successfully connected to MongoDB!")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """
    Close MongoDB connection on application shutdown
    """
    print("Closing MongoDB connection...")
    db.client.close()
    print("✅ MongoDB connection closed")


def get_database():
    """
    Get database instance
    Returns: MongoDB database object
    """
    return db.client[settings.MONGODB_DB]

def get_trades_database():
    """
    Get trades database instance
    Returns: MongoDB trades database object
    """
    return db.client["trades_db"]
