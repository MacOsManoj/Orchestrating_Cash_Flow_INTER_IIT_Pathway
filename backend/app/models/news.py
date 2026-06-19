"""
News-related Pydantic models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PublisherInfo(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    url: str
    source: str
    published_at: str


class EnrichedArticle(BaseModel):
    article_id: str
    title: str
    url: str
    source: str
    published_at: str
    company: str
    factor_type: str
    content: str
    content_length: int
    content_quality: Optional[str] = None
    publisher_name: Optional[str] = None
    author: Optional[str] = None
    publisher_icon: Optional[str] = None
    sentiment_label: str
    sentiment_score: float
    sentiment_confidence: Optional[str] = None
    liquidity_impact: str
    critical_events: str
    decisions: str
    cluster_id: str
    enriched_at: str


class SummarizedArticle(BaseModel):
    article_id: str
    title: str
    url: str
    company: str
    factor_type: str
    published_at: str
    source: str
    # Enriched fields
    content: str
    content_length: int
    content_quality: Optional[str] = None
    publisher_name: Optional[str] = None
    author: Optional[str] = None
    publisher_icon: Optional[str] = None
    sentiment_label: str
    sentiment_score: float
    sentiment_confidence: Optional[str] = None
    liquidity_impact: str
    critical_events: str
    decisions: str
    cluster_id: str
    enriched_at: str
    # LLM summary fields
    is_relevant: Optional[bool] = None
    relevance_reason: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None
    financial_metrics: Optional[dict] = None
    impact_assessment: Optional[str] = None
    summarized_at: Optional[str] = None
    worker_id: Optional[str] = None


class CompanyQuery(BaseModel):
    company_code: str
    theme: str
    query: str


class CompanyConfig(BaseModel):
    company_code: str
    aliases: List[str]
    queries: dict


class SearchConfigUpdate(BaseModel):
    """Request body for updating search config"""

    company_code: str
    theme: str
    query: str


class ArticleFilters(BaseModel):
    """Query parameters for filtering articles"""

    company: Optional[str] = None
    factor_type: Optional[str] = None
    sentiment: Optional[str] = None
    liquidity_impact: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    source: Optional[str] = None
    limit: int = Field(default=50, le=200)
    skip: int = Field(default=0, ge=0)
