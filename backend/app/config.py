from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from .env file
    """

    # MongoDB settings - use MONGODB_URI for consistency with other services
    MONGODB_URI: str = (
        "mongodb+srv://admin:admin@cluster0.xfoccu0.mongodb.net/?appName=Cluster0"
    )
    MONGODB_DB: str = "news_db"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"

    # LLM Configurationj
    GEMINI_API_KEY: str = ""

    # HeyGen Video Configuration
    HEYGEN_API_KEY: str = ""
    HEYGEN_AVATAR_ID: str = "Aditya_public_1"
    HEYGEN_VOICE_ID: str = "5a09177ef53140db864193c7e1cc464d"

    # News API Configuration
    NEWS_API_URL: str = "http://localhost:8000/api/news/summarized"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )


# Create single instance
settings = Settings()
