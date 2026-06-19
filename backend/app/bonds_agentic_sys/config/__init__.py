"""
Agent Bond V2 - Configuration Module
System configuration and settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Model Configuration
DEFAULT_LLM_MODEL = "gpt-4-turbo-preview"
DEFAULT_LLM_TEMPERATURE = 0.0

# Paths - using .cache for real data (not files-mock since we use real MCP data)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VECTOR_DB_PATH = os.path.join(PROJECT_ROOT, "vector_store")
CACHE_DIR = os.path.join(PROJECT_ROOT, ".cache")

# RAG Configuration
RAG_ENABLED = True
CACHE_ENABLED = True

# Data Files
BOND_DATA_FILE = os.path.join(DATA_DIR, "Final_Bond_Data.csv")
FEATURES_FILE = os.path.join(DATA_DIR, "combined_with_quarterly_features.csv")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_PATH, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
