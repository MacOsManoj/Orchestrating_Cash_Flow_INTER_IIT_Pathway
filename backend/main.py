# main.py

import logging

# Configure logging FIRST before any other imports
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chats import router as chats_router
from app.routes.versions import router as versions_router
from app.routes.cashflow_router import router as cashflow_router
from app.routes import news  
from app.routes import video 
from app.routes.stocks import router as stocks_router  
from app.routes.forex import (
    router as forex_router,
    initialize_forex_services,
)  
from app.database import connect_to_mongo, close_mongo_connection  
from app.services.scheduler import start_scheduler  
from dotenv import load_dotenv
from app.routes.news_search import load_sentiment_model
from app.routes.bond_router import router as bond_router  
from app.routes.news_search import load_sentiment_model
from app.routes.portfolio_trades import (
    router as portfolio_router,
)  
from app.routes.orchestrator import router as orchestrator_router

import os


load_dotenv()  # Load environment variables from .env file
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🔌 DB startup/shutdown hooks
@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    load_sentiment_model()
    start_scheduler()  # Start video generation scheduler
    initialize_forex_services()  # Initialize forex pipeline and agent


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


# Include routers
app.include_router(chats_router)
app.include_router(versions_router)
app.include_router(cashflow_router, prefix="/api/cashflow", tags=["Cashflow"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(video.router, prefix="/api/video", tags=["Video"])
app.include_router(stocks_router)  # Stocks routes

# Forex routes


app.include_router(forex_router, prefix="/api/forex", tags=["Forex"])

# Bond routes

app.include_router(bond_router, prefix="/api/bonds", tags=["Bonds"])

# Portfolio/Trades routes
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["Portfolio"])

# Master Orchestrator routes
app.include_router(orchestrator_router, prefix="/api/orchestrator", tags=["Orchestrator"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
