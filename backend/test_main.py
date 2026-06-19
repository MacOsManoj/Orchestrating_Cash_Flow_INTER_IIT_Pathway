# test_main.py

import logging

# Configure logging FIRST before any other imports
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Skip imports that might require DB
# from app.routes.chats import router as chats_router
# from app.routes.versions import router as versions_router
# from app.routes import news  # ⬅️ import news router
# from app.routes import video  # ⬅️ import video router

from app.routes.forex import router as forex_router, initialize_forex_services

# from app.database import connect_to_mongo, close_mongo_connection
# from app.services.scheduler import start_scheduler
from dotenv import load_dotenv

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
    # await connect_to_mongo()
    # start_scheduler()  # Start video generation scheduler
    initialize_forex_services()  # Initialize forex pipeline and agent


@app.on_event("shutdown")
async def shutdown_event():
    # await close_mongo_connection()
    pass


# Include routers
# app.include_router(chats_router)
# app.include_router(versions_router)
# app.include_router(news.router, prefix="/api/news", tags=["News"])
# app.include_router(video.router, prefix="/api/video", tags=["Video"])
app.include_router(forex_router)  # Forex routes (already has /forex prefix)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
