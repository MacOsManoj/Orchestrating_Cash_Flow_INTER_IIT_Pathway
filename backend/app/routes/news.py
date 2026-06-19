"""
News API Routes
- Fetch summarized articles (with filters)
- Fetch enriched articles (with filters)
- Update search config
- Fetch companies list
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pymongo import DESCENDING
from app.database import get_database
from app.routes.news_search import run_news_search
from app.models.news import (
    SummarizedArticle,
    EnrichedArticle,
    CompanyConfig,
    SearchConfigUpdate,
    ArticleFilters,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ==========================================
# Summarized Articles
# ==========================================


@router.get("/summarized", response_model=List[SummarizedArticle])
async def get_summarized_articles(
    company: Optional[str] = Query(None, description="Filter by company code"),
    factor_type: Optional[str] = Query(
        None, description="Filter by factor type (political, regulatory, etc)"
    ),
    sentiment: Optional[str] = Query(
        None, description="Filter by sentiment (positive, negative, neutral)"
    ),
    liquidity_impact: Optional[str] = Query(
        None, description="Filter by liquidity impact (high, medium, low)"
    ),
    start_date: Optional[str] = Query(
        None, description="Start date (ISO format: 2024-01-01)"
    ),
    end_date: Optional[str] = Query(
        None, description="End date (ISO format: 2024-12-31)"
    ),
    source: Optional[str] = Query(None, description="Filter by source"),
    is_relevant: Optional[bool] = Query(
        None, description="Filter by relevance (true/false)"
    ),
    limit: int = Query(50, le=200, description="Max results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip (pagination)"),
):
    """
    Get summarized articles with optional filters

    Example: /api/news/summarized?company=TCS&sentiment=negative&limit=10
    """
    db = get_database()

    # Build MongoDB filter query
    filter_query = {}

    if company:
        filter_query["company"] = company.upper()  # Ticker symbols stored uppercase
    if factor_type:
        filter_query["factor_type"] = factor_type.lower()
    if sentiment:
        filter_query["sentiment_label"] = sentiment.lower()
    if liquidity_impact:
        # Liquidity impact is stored in uppercase (e.g., HIGH_POSITIVE, NEUTRAL)
        filter_query["liquidity_impact"] = liquidity_impact.upper()
    if source:
        filter_query["source"] = {"$regex": source, "$options": "i"}
    if is_relevant is not None:
        filter_query["is_relevant"] = is_relevant

    # Date range filter
    if start_date or end_date:
        filter_query["published_at"] = {}
        if start_date:
            filter_query["published_at"]["$gte"] = start_date
        if end_date:
            filter_query["published_at"]["$lte"] = end_date

    try:
        # Query MongoDB
        cursor = (
            db.summarize.find(filter_query)
            .sort("published_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        articles = await cursor.to_list(length=limit)

        if len(articles) == 0:
            # Fallback to search when DB is empty
            articles = await run_news_search(company.lower())

            # Filter by relevance
            articles = [a for a in articles if a.get("is_relevant", True)]

            # Filter by financial impact if specified
            if liquidity_impact:
                articles = [
                    a
                    for a in articles
                    if a.get("liquidity_impact", "").upper() == liquidity_impact.upper()
                ]

            logger.info(
                f"Retrieved {len(articles)} articles from search (filters: {filter_query})"
            )
            return articles

        # Convert ObjectId to string
        for article in articles:
            if "_id" in article:
                article["_id"] = str(article["_id"])

        logger.info(
            f"Retrieved {len(articles)} summarized articles (filters: {filter_query})"
        )
        return articles

    except Exception as e:
        logger.error(f"Error fetching summarized articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Enriched Articles
# ==========================================


@router.get("/enriched", response_model=List[EnrichedArticle])
async def get_enriched_articles(
    company: Optional[str] = Query(None, description="Filter by company code"),
    factor_type: Optional[str] = Query(None, description="Filter by factor type"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    liquidity_impact: Optional[str] = Query(
        None, description="Filter by liquidity impact"
    ),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, le=200, description="Max results"),
    skip: int = Query(0, ge=0, description="Skip results (pagination)"),
):
    """
    Get enriched articles (with sentiment but no LLM summary) with filters

    Example: /api/news/enriched?company=ITC&factor_type=regulatory&limit=20
    """
    db = get_database()

    # Build MongoDB filter query
    filter_query = {}

    if company:
        filter_query["company"] = company.upper()  # Ticker symbols stored uppercase
    if factor_type:
        filter_query["factor_type"] = factor_type.lower()
    if sentiment:
        filter_query["sentiment_label"] = sentiment.lower()
    if liquidity_impact:
        # Liquidity impact is stored in uppercase (e.g., HIGH_POSITIVE, NEUTRAL)
        filter_query["liquidity_impact"] = liquidity_impact.upper()
    if source:
        filter_query["source"] = {"$regex": source, "$options": "i"}

    # Date range filter
    if start_date or end_date:
        filter_query["published_at"] = {}
        if start_date:
            filter_query["published_at"]["$gte"] = start_date
        if end_date:
            filter_query["published_at"]["$lte"] = end_date

    try:
        cursor = (
            db.enriched_articles.find(filter_query)
            .sort("published_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        articles = await cursor.to_list(length=limit)

        for article in articles:
            if "_id" in article:
                article["_id"] = str(article["_id"])

        logger.info(
            f"Retrieved {len(articles)} enriched articles (filters: {filter_query})"
        )
        return articles

    except Exception as e:
        logger.error(f"Error fetching enriched articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Story Clusters
# ==========================================


@router.get("/clusters")
async def get_story_clusters(
    company: Optional[str] = Query(None),
    factor_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
):
    """
    Get story clusters (aggregated news from multiple sources)

    Example: /api/news/clusters?company=tcs&limit=10
    """
    db = get_database()

    filter_query = {}
    if company:
        filter_query["company"] = company.upper()  # Ticker symbols stored uppercase
    if factor_type:
        filter_query["factor_type"] = factor_type.lower()
    if start_date:
        filter_query["published_at"] = {"$gte": start_date}

    try:
        cursor = (
            db.story_clusters.find(filter_query)
            .sort("last_updated", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        clusters = await cursor.to_list(length=limit)

        for cluster in clusters:
            if "_id" in cluster:
                cluster["_id"] = str(cluster["_id"])

        logger.info(f"Retrieved {len(clusters)} story clusters")
        return clusters

    except Exception as e:
        logger.error(f"Error fetching clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Search Config Management
# ==========================================


@router.get("/companies", response_model=List[CompanyConfig])
async def get_companies():
    """
    Get list of all companies with their search queries

    Returns: List of companies with aliases and pre-built queries
    """
    db = get_database()

    try:
        # Get config from config_db.search_config
        config = await db.client.config_db.search_config.find_one(
            {"_id": "search_config_v1"}
        )

        if not config:
            raise HTTPException(status_code=404, detail="Search config not found")

        companies_data = config.get("companies", {})

        # Convert to list format
        companies = []
        for code, data in companies_data.items():
            companies.append(
                {
                    "company_code": code,
                    "aliases": data.get("aliases", []),
                    "queries": data.get("queries", {}),
                }
            )

        logger.info(f"Retrieved {len(companies)} companies")
        return companies

    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_search_config(update: SearchConfigUpdate):
    """
    Update a search query for a specific company and theme

    Request body:
    {
        "company_code": "tcs",
        "theme": "regulatory",
        "query": "(\"TCS\" OR \"TCS Ltd\") AND (regulation OR compliance) -job -jobs"
    }
    """
    db = get_database()

    try:
        # Update the specific query in the config
        result = await db.client.config_db.search_config.update_one(
            {"_id": "search_config_v1"},
            {
                "$set": {
                    f"companies.{update.company_code}.queries.{update.theme}": update.query
                }
            },
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Config not found")

        logger.info(f"Updated config for {update.company_code} - {update.theme}")
        return {
            "message": "Search config updated successfully",
            "company": update.company_code,
            "theme": update.theme,
        }

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/company")
async def add_company(company_code: str, aliases: List[str]):
    """
    Add a new company to the search config

    Request body:
    {
        "company_code": "apple",
        "aliases": ["Apple", "Apple INC", "App Store", "iPhone"]
    }
    """
    db = get_database()

    try:
        # Get existing config to build queries
        config = await db.client.config_db.search_config.find_one(
            {"_id": "search_config_v1"}
        )

        if not config:
            raise HTTPException(status_code=404, detail="Config not found")

        # Build queries for all themes
        risk_themes = config.get("risk_themes", {})
        negative_terms = config.get("negative_terms", "")

        if not risk_themes:
            raise HTTPException(
                status_code=500,
                detail="No risk_themes found in config. Run setup_search_config.py first.",
            )

        queries = {}
        for theme, theme_query in risk_themes.items():
            # Build: ("Apple" OR "Apple INC" OR ...) AND (earnings OR revenue OR ...)
            alias_part = " OR ".join(f'"{alias}"' for alias in aliases)
            company_part = f"({alias_part})"
            full_query = f"{company_part} AND {theme_query}"
            if negative_terms:
                full_query += f" {negative_terms}"
            queries[theme] = full_query

        # Add company to config
        result = await db.client.config_db.search_config.update_one(
            {"_id": "search_config_v1"},
            {
                "$set": {
                    f"companies.{company_code}": {
                        "aliases": aliases,
                        "queries": queries,
                    }
                }
            },
        )

        logger.info(f"Added new company: {company_code} with {len(queries)} queries")
        return {
            "message": "Company added successfully",
            "company_code": company_code,
            "aliases": aliases,
            "queries_created": len(queries),
            "queries": queries,  # Show what was created
        }

    except Exception as e:
        logger.error(f"Error adding company: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Statistics
# ==========================================


@router.get("/stats")
async def get_news_stats():
    """
    Get statistics about the news pipeline

    Returns: Article counts, companies, sentiment distribution, etc.
    """
    db = get_database()

    try:
        stats = {}

        # Total articles
        stats["total_enriched"] = await db.enriched_articles.count_documents({})
        stats["total_summarized"] = await db.summarize.count_documents({})
        stats["total_clusters"] = await db.story_clusters.count_documents({})

        # Articles by company
        pipeline = [
            {"$group": {"_id": "$company", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        by_company = await db.summarize.aggregate(pipeline).to_list(None)
        stats["by_company"] = {item["_id"]: item["count"] for item in by_company}

        # Sentiment distribution
        pipeline = [{"$group": {"_id": "$sentiment_label", "count": {"$sum": 1}}}]
        by_sentiment = await db.summarize.aggregate(pipeline).to_list(None)
        stats["by_sentiment"] = {item["_id"]: item["count"] for item in by_sentiment}

        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow().isoformat()[:10]  # Simple date filter
        stats["today_count"] = await db.summarize.count_documents(
            {"published_at": {"$gte": yesterday}}
        )

        logger.info("Retrieved news statistics")
        return stats

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
