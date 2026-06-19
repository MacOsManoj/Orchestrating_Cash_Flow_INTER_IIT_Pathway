"""
FastAPI v1 endpoints for Bond Data API
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.bonds_agentic_sys.orchestrator_v3 import create_orchestrator_v3
from app.bonds_agentic_sys.schemas_v2 import SystemConfigV2
from app.bonds.api_functions.bond_data_processor import (
    get_bond_by_isin,
    get_all_bonds,
    load_bond_data,
    extract_coupon_info,
)
from app.bonds.api_functions.models import (
    BondDetails,
    BondSummary,
    QueryRequest,
    QueryResponse,
    OutputResponse,
    YieldDataPoint,
    YieldMetrics,
    YieldHistoryResponse,
    RateYieldDataPoint,
    SeriesDefinition,
    YAxisConfig,
    RateYieldOverlayResponse,
    PriceStatisticsDataPoint,
    PriceStatisticsMetrics,
    PriceStatisticsResponse,
    BondSearchResult,
    SearchResponse,
    ComparisonInstrument,
    ComparisonListResponse,
    ComparisonDetailsResponse,
    AddToComparisonRequest,
    ChatRequest,
    ChatResponse,
    RecommendationResponse,
)
from app.bonds.api_functions.agent_service import (
    process_query,
    get_stored_query,
    is_orchestrator_available,
    extract_output_text_from_state,
)
from app.bonds.api_functions.yield_data_processor import get_yield_history
from app.bonds.api_functions.rate_yield_processor import get_rate_yield_overlay
from app.bonds.api_functions.price_statistics_processor import get_price_statistics
from app.bonds.api_functions.comparison_service import (
    search_bonds,
    get_comparison_list,
    add_to_comparison,
    remove_from_comparison,
    get_comparison_details,
    extract_bond_name_from_description,
    extract_issuer_from_description,
    calculate_current_yield,
    calculate_yield_change_info,
)


router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint"""
    endpoints = {
        "bond_details": "/{isin}",
        "bond_universe": "/universe",
        "price_statistics": "/{isin}/price-statistics",
    }

    if is_orchestrator_available():
        endpoints.update(
            {
                "agent_query": "POST /api/v1/agent/query",
                "agent_output": "GET /api/v1/agent/output?query_id={query_id}",
            }
        )

    return {"message": "Bond Data API v1", "endpoints": endpoints}


@router.get("/universe", response_model=List[BondSummary])
async def get_bond_universe(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    rating: Optional[str] = Query(None, description="Filter by credit rating"),
    region: Optional[str] = Query(None, description="Filter by region"),
    search: Optional[str] = Query(
        None, description="Search by bond name, ticker, or ISIN"
    ),
):
    """
    Get all bonds in the universe.

    Query Parameters (all optional):
    - sector: Filter by sector
    - rating: Filter by credit rating
    - region: Filter by region
    - search: Search by bond name, ticker, or ISIN

    Returns list of all bonds if no filters provided.
    """
    bonds = get_all_bonds()

    # Apply filters if provided
    if search:
        search_lower = search.lower()
        bonds = [
            b
            for b in bonds
            if search_lower in b["isin"].lower()
            or search_lower in b["bond_name"].lower()
        ]

    return [BondSummary(**bond) for bond in bonds]


# Note: More specific routes must come before dynamic routes
# Compare routes must come before {isin} route
@router.get("/compare/search", response_model=SearchResponse)
async def search_bonds_for_comparison(
    query: str = Query(..., description="Search query (ISIN or name)"),
    limit: int = Query(10, description="Maximum number of results"),
):
    """
    Search for bonds/instruments to add to comparison.

    Query Parameters:
    - query: Search query (ISIN or name) (required)
    - limit: Maximum number of results (default: 10)

    Returns list of matching bonds with yield information.
    """
    results = search_bonds(query, limit)
    return SearchResponse(
        results=[BondSearchResult(**result) for result in results],
        total_results=len(results),
    )


@router.get("/compare", response_model=ComparisonListResponse)
async def get_comparison_list_endpoint(
    user_id: Optional[str] = Query(None, description="User identifier"),
    session_id: Optional[str] = Query(None, description="Session identifier"),
):
    """
    Get list of instruments currently being compared.

    Query Parameters:
    - user_id: User identifier (optional)
    - session_id: Session identifier for temporary comparisons (optional)

    Returns current comparison list with yield information.
    """
    comparison = get_comparison_list(user_id, session_id)
    return ComparisonListResponse(
        comparison_id=comparison["comparison_id"],
        instruments=[
            ComparisonInstrument(**inst) for inst in comparison["instruments"]
        ],
        created_at=comparison["created_at"],
        last_updated=comparison["last_updated"],
    )


@router.post("/compare/add", response_model=ComparisonListResponse)
async def add_to_comparison_endpoint(request: AddToComparisonRequest):
    """
    Add bond to comparison list.

    Request Body:
    - isin: ISIN identifier (required)
    - user_id: User identifier (optional)
    - session_id: Session identifier (optional)

    Returns updated comparison list.
    """
    try:
        comparison = add_to_comparison(
            request.isin, request.user_id, request.session_id
        )
        return ComparisonListResponse(
            comparison_id=comparison["comparison_id"],
            instruments=[
                ComparisonInstrument(**inst) for inst in comparison["instruments"]
            ],
            created_at=comparison["created_at"],
            last_updated=comparison["last_updated"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/compare/remove", response_model=ComparisonListResponse)
async def remove_from_comparison_endpoint(
    isin: str = Query(..., description="ISIN identifier"),
    user_id: Optional[str] = Query(None, description="User identifier"),
    session_id: Optional[str] = Query(None, description="Session identifier"),
):
    """
    Remove bond from comparison list.

    Query Parameters:
    - isin: ISIN identifier (required)
    - user_id: User identifier (optional)
    - session_id: Session identifier (optional)

    Returns updated comparison list.
    """
    try:
        comparison = remove_from_comparison(isin, user_id, session_id)
        return ComparisonListResponse(
            comparison_id=comparison["comparison_id"],
            instruments=[
                ComparisonInstrument(**inst) for inst in comparison["instruments"]
            ],
            created_at=comparison["created_at"],
            last_updated=comparison["last_updated"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/compare/{comparison_id}/details", response_model=ComparisonDetailsResponse
)
async def get_comparison_details_endpoint(comparison_id: str):
    """
    Get detailed comparison data by comparison_id.

    Path Parameters:
    - comparison_id: Comparison identifier (required)

    Returns detailed comparison data.
    """
    comparison = get_comparison_details(comparison_id)
    if comparison is None:
        raise HTTPException(
            status_code=404, detail=f"Comparison with ID {comparison_id} not found"
        )

    return ComparisonDetailsResponse(
        comparison_id=comparison["comparison_id"],
        instruments=[
            ComparisonInstrument(**inst) for inst in comparison["instruments"]
        ],
        created_at=comparison["created_at"],
        last_updated=comparison["last_updated"],
    )


@router.get("/universe/compare", response_model=SearchResponse)
async def get_bond_universe_for_comparison(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    rating: Optional[str] = Query(None, description="Filter by credit rating"),
    search: Optional[str] = Query(None, description="Search by bond name or ISIN"),
):
    """
    Get all bonds with info needed for comparison.

    Query Parameters:
    - sector: Filter by sector (optional)
    - rating: Filter by credit rating (optional)
    - search: Search by bond name or ISIN (optional)

    Returns all bonds from Final_Bond_Data.csv with comparison-relevant information.
    """
    import pandas as pd

    bond_df = load_bond_data()
    results = []

    for _, row in bond_df.iterrows():
        try:
            isin = str(row.get("ISIN", "")).strip()
            isin_desc = str(row.get("ISIN Description", "")).strip()

            # Apply search filter if provided
            if search:
                search_upper = search.upper().strip()
                if (
                    search_upper not in isin.upper()
                    and search_upper not in isin_desc.upper()
                ):
                    continue

            # Extract bond info
            bond_name = extract_bond_name_from_description(isin_desc)
            issuer = extract_issuer_from_description(isin_desc)
            coupon_rate = extract_coupon_info(isin_desc)
            if coupon_rate is None:
                # FALLBACK: Default coupon rate when not found in description
                coupon_rate = 0.07  # Default fallback

            maturity_date = str(row.get("Maturity Date", "")).strip()

            # Get current price
            ltp = row.get("LTP", 0.0)
            try:
                ltp_value = (
                    float(ltp) if pd.notna(ltp) and str(ltp).strip() != "-" else 0.0
                )
            except (ValueError, TypeError):
                ltp_value = 0.0

            prev_close = row.get("PREV.CLOSE", 0.0)
            try:
                prev_close_value = (
                    float(prev_close)
                    if pd.notna(prev_close) and str(prev_close).strip() != "-"
                    else 0.0
                )
            except (ValueError, TypeError):
                prev_close_value = 0.0

            current_price = ltp_value if ltp_value > 0 else prev_close_value
            if current_price == 0:
                # FALLBACK: Default to face value when price data is missing
                current_price = 100.0  # Default to face value

            # Calculate current yield
            current_yield = calculate_current_yield(coupon_rate, current_price)
            current_yield_percent = current_yield * 100

            # Get yield change info
            pct_change = row.get("%CHNG", 0.0)
            try:
                pct_change_value = float(pct_change) if pd.notna(pct_change) else 0.0
            except (ValueError, TypeError):
                pct_change_value = 0.0

            yield_change_info = calculate_yield_change_info(pct_change_value)

            results.append(
                {
                    "isin": isin,
                    "name": bond_name,
                    "issuer": issuer,
                    "coupon_rate": coupon_rate,
                    "maturity_date": maturity_date,
                    "current_yield": current_yield,
                    "current_yield_percent": round(current_yield_percent, 2),
                    "yield_change": yield_change_info["yield_change"],
                    "yield_change_direction": yield_change_info[
                        "yield_change_direction"
                    ],
                }
            )
        except Exception:
            continue

    return SearchResponse(
        results=[BondSearchResult(**result) for result in results],
        total_results=len(results),
    )


@router.get("/{isin}", response_model=BondDetails)
async def get_bond_details(isin: str):
    """
    Get comprehensive bond details by ISIN.

    Returns:
    - Bond Details: coupon_rate, maturity_date, next_coupon_date, minimum_increment
    - Pricing Information: last_price, clean_price, accrued_interest, ytm
    - Risk Metrics: duration, convexity, dv01, z_spread, var
    - Volatility Metrics: interest_rate_volatility, credit_spread_volatility
    - Metadata: bond_name, isin, credit_rating (optional)
    """
    bond_data = get_bond_by_isin(isin)

    if bond_data is None:
        raise HTTPException(status_code=404, detail=f"Bond with ISIN {isin} not found")

    return BondDetails(**bond_data)


@router.post("/agent/query", response_model=QueryResponse)
async def submit_query(request: QueryRequest):
    """
    Submit a query to the agent.

    Request body:
    - user_id: User identifier
    - query: User query text
    - isin: Optional ISIN for bond-specific queries
    - context: Optional context dictionary

    Returns query_id, status, processing_time, and timestamp.
    Use query_id to retrieve output via GET /api/v1/agent/output
    """
    # Process query through agent service
    result = await process_query(
        user_id=request.user_id, query=request.query, conversation_history=None
    )

    return QueryResponse(
        query_id=result["query_id"],
        status=result["status"],
        processing_time=result["processing_time"],
        timestamp=result["timestamp"],
    )


@router.get("/agent/output", response_model=OutputResponse)
async def get_output(
    query_id: str = Query(..., description="Query identifier"),
    user_id: Optional[str] = Query(None, description="User identifier"),
):
    """
    Get the final text output from the agent's langraph state.

    Query Parameters:
    - query_id: Query identifier from the agent response (required)
    - user_id: User identifier (optional)

    The output comes from the Response agent (to be implemented later).
    For now, extracts from state.advisory.summary or similar fields.
    """
    stored_data = get_stored_query(query_id)

    if not stored_data:
        raise HTTPException(
            status_code=404, detail=f"Query with ID {query_id} not found"
        )

    # Optional user_id validation
    if user_id and stored_data.get("user_id") != user_id:
        raise HTTPException(
            status_code=403, detail="Query ID does not belong to this user"
        )

    # Get state from storage
    state = stored_data.get("state")
    if not state:
        raise HTTPException(
            status_code=404, detail="State data not available for this query"
        )

    # Extract text output (will be from Response agent later)
    output_text = extract_output_text_from_state(state)

    return OutputResponse(
        query_id=query_id,
        user_query=stored_data.get("user_query", ""),
        output=output_text,
        timestamp=stored_data.get("timestamp", datetime.now().isoformat()),
    )


@router.get("/{isin}/yield-history", response_model=YieldHistoryResponse)
async def get_yield_history_endpoint(
    isin: str,
    period: str = Query("1D", description="Time period: 1D, 1W, 1M, 1Y, YTD, MAX"),
):
    """
    Get yield history data for charts and yield-related metrics.

    Query Parameters:
    - period: Time period - 1D, 1W, 1M, 1Y, YTD, or MAX (default: 1D)

    Returns:
    - yield_data: Array of yield data points with date, yield, and time
    - metrics: Current yielding, 1-month change, volatility (20D σ), max drawdown (1Y)
    """
    # Validate period
    valid_periods = ["1D", "1W", "1M", "1Y", "YTD", "MAX"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
        )

    # Get yield history
    yield_data = get_yield_history(isin, period)

    if yield_data is None:
        raise HTTPException(
            status_code=404, detail=f"Yield history not found for bond with ISIN {isin}"
        )

    # Convert to Pydantic models
    # Note: yield_data uses "yield" key, but Python keyword requires "yield_value"
    yield_points = []
    for point in yield_data["yield_data"]:
        # Rename "yield" to "yield_value" for Pydantic model
        point_copy = point.copy()
        if "yield" in point_copy:
            point_copy["yield_value"] = point_copy.pop("yield")
        yield_points.append(YieldDataPoint(**point_copy))

    metrics = YieldMetrics(**yield_data["metrics"])

    return YieldHistoryResponse(
        isin=yield_data["isin"],
        period=yield_data["period"],
        yield_data=yield_points,
        metrics=metrics,
        last_updated=yield_data["last_updated"],
    )


@router.get("/{isin}/rate-yield-overlay", response_model=RateYieldOverlayResponse)
async def get_rate_yield_overlay_endpoint(
    isin: str, period: str = Query("1Y", description="Time period: 5Y, 3Y, 1Y, YTD")
):
    """
    Get rate vs yield overlay data for chart display.

    Query Parameters:
    - period: Time period - 5Y, 3Y, 1Y, or YTD (default: 1Y)

    Returns:
    - data: Array of {date, policy_rate, yield_10y} points
    - series: Series definitions for Policy Rate and 10Y Yield
    - y_axes: Y-axis configurations
    """
    # Validate period
    valid_periods = ["5Y", "3Y", "1Y", "YTD"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
        )

    # Get overlay data
    overlay_data = get_rate_yield_overlay(isin, period)

    if overlay_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rate vs yield overlay data not found for bond with ISIN {isin}",
        )

    # Convert to Pydantic models
    data_points = [RateYieldDataPoint(**point) for point in overlay_data["data"]]
    series = [SeriesDefinition(**s) for s in overlay_data["series"]]
    y_axes = {
        key: YAxisConfig(**config) for key, config in overlay_data["y_axes"].items()
    }

    return RateYieldOverlayResponse(
        isin=overlay_data["isin"],
        period=overlay_data["period"],
        data=data_points,
        series=series,
        y_axes=y_axes,
        last_updated=overlay_data["last_updated"],
    )


@router.get("/{isin}/price-statistics", response_model=PriceStatisticsResponse)
async def get_price_statistics_endpoint(
    isin: str,
    period: str = Query("1D", description="Time period: 1D, 1W, 1M, 3M, YTD, 1Y, MAX"),
):
    """
    Get price statistics data for charts and metrics.

    Query Parameters:
    - period: Time period - 1D, 1W, 1M, 3M, YTD, 1Y, or MAX (default: 1D)

    Returns:
    - price_data: Array of price data points with percentile bands
    - metrics: Median price, 5th percentile, 95th percentile, implied volatility
    """
    # Validate period
    valid_periods = ["1D", "1W", "1M", "3M", "YTD", "1Y", "MAX"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
        )

    # Get price statistics
    price_stats = get_price_statistics(isin, period)

    if price_stats is None:
        raise HTTPException(
            status_code=404,
            detail=f"Price statistics not found for bond with ISIN {isin}",
        )

    # Convert to Pydantic models
    price_points = [
        PriceStatisticsDataPoint(**point) for point in price_stats["price_data"]
    ]
    metrics = PriceStatisticsMetrics(**price_stats["metrics"])

    return PriceStatisticsResponse(
        isin=price_stats["isin"],
        period=price_stats["period"],
        price_data=price_points,
        metrics=metrics,
        last_updated=price_stats["last_updated"],
    )


@router.get("/compare/search", response_model=SearchResponse)
async def search_bonds_for_comparison(
    query: str = Query(..., description="Search query (ISIN or name)"),
    limit: int = Query(10, description="Maximum number of results"),
):
    """
    Search for bonds/instruments to add to comparison.

    Query Parameters:
    - query: Search query (ISIN or name) (required)
    - limit: Maximum number of results (default: 10)

    Returns list of matching bonds with yield information.
    """
    results = search_bonds(query, limit)
    return SearchResponse(
        results=[BondSearchResult(**result) for result in results],
        total_results=len(results),
    )


@router.get("/compare", response_model=ComparisonListResponse)
async def get_comparison_list_endpoint(
    user_id: Optional[str] = Query(None, description="User identifier"),
    session_id: Optional[str] = Query(None, description="Session identifier"),
):
    """
    Get list of instruments currently being compared.

    Query Parameters:
    - user_id: User identifier (optional)
    - session_id: Session identifier for temporary comparisons (optional)

    Returns current comparison list with yield information.
    """
    comparison = get_comparison_list(user_id, session_id)
    return ComparisonListResponse(
        comparison_id=comparison["comparison_id"],
        instruments=[
            ComparisonInstrument(**inst) for inst in comparison["instruments"]
        ],
        created_at=comparison["created_at"],
        last_updated=comparison["last_updated"],
    )


@router.post("/compare/add", response_model=ComparisonListResponse)
async def add_to_comparison_endpoint(request: AddToComparisonRequest):
    """
    Add bond to comparison list.

    Request Body:
    - isin: ISIN identifier (required)
    - user_id: User identifier (optional)
    - session_id: Session identifier (optional)

    Returns updated comparison list.
    """
    try:
        comparison = add_to_comparison(
            request.isin, request.user_id, request.session_id
        )
        return ComparisonListResponse(
            comparison_id=comparison["comparison_id"],
            instruments=[
                ComparisonInstrument(**inst) for inst in comparison["instruments"]
            ],
            created_at=comparison["created_at"],
            last_updated=comparison["last_updated"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/compare/remove", response_model=ComparisonListResponse)
async def remove_from_comparison_endpoint(
    isin: str = Query(..., description="ISIN identifier"),
    user_id: Optional[str] = Query(None, description="User identifier"),
    session_id: Optional[str] = Query(None, description="Session identifier"),
):
    """
    Remove bond from comparison list.

    Query Parameters:
    - isin: ISIN identifier (required)
    - user_id: User identifier (optional)
    - session_id: Session identifier (optional)

    Returns updated comparison list.
    """
    try:
        comparison = remove_from_comparison(isin, user_id, session_id)
        return ComparisonListResponse(
            comparison_id=comparison["comparison_id"],
            instruments=[
                ComparisonInstrument(**inst) for inst in comparison["instruments"]
            ],
            created_at=comparison["created_at"],
            last_updated=comparison["last_updated"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/compare/{comparison_id}/details", response_model=ComparisonDetailsResponse
)
async def get_comparison_details_endpoint(comparison_id: str):
    """
    Get detailed comparison data by comparison_id.

    Path Parameters:
    - comparison_id: Comparison identifier (required)

    Returns detailed comparison data.
    """
    comparison = get_comparison_details(comparison_id)
    if comparison is None:
        raise HTTPException(
            status_code=404, detail=f"Comparison with ID {comparison_id} not found"
        )

    return ComparisonDetailsResponse(
        comparison_id=comparison["comparison_id"],
        instruments=[
            ComparisonInstrument(**inst) for inst in comparison["instruments"]
        ],
        created_at=comparison["created_at"],
        last_updated=comparison["last_updated"],
    )


@router.get("/universe/compare", response_model=SearchResponse)
async def get_bond_universe_for_comparison(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    rating: Optional[str] = Query(None, description="Filter by credit rating"),
    search: Optional[str] = Query(None, description="Search by bond name or ISIN"),
):
    """
    Get all bonds with info needed for comparison.

    Query Parameters:
    - sector: Filter by sector (optional)
    - rating: Filter by credit rating (optional)
    - search: Search by bond name or ISIN (optional)

    Returns all bonds from Final_Bond_Data.csv with comparison-relevant information.
    """
    from bonds.api_functions.bond_data_processor import get_all_bonds
    import pandas as pd

    bond_df = load_bond_data()
    results = []

    for _, row in bond_df.iterrows():
        try:
            isin = str(row.get("ISIN", "")).strip()
            isin_desc = str(row.get("ISIN Description", "")).strip()

            # Apply search filter if provided
            if search:
                search_upper = search.upper().strip()
                if (
                    search_upper not in isin.upper()
                    and search_upper not in isin_desc.upper()
                ):
                    continue

            # Extract bond info
            bond_name = extract_bond_name_from_description(isin_desc)
            issuer = extract_issuer_from_description(isin_desc)
            coupon_rate = extract_coupon_info(isin_desc)
            if coupon_rate is None:
                # FALLBACK: Default coupon rate when not found in description
                coupon_rate = 0.07  # Default fallback

            maturity_date = str(row.get("Maturity Date", "")).strip()

            # Get current price
            ltp = row.get("LTP", 0.0)
            try:
                ltp_value = (
                    float(ltp) if pd.notna(ltp) and str(ltp).strip() != "-" else 0.0
                )
            except (ValueError, TypeError):
                ltp_value = 0.0

            prev_close = row.get("PREV.CLOSE", 0.0)
            try:
                prev_close_value = (
                    float(prev_close)
                    if pd.notna(prev_close) and str(prev_close).strip() != "-"
                    else 0.0
                )
            except (ValueError, TypeError):
                prev_close_value = 0.0

            current_price = ltp_value if ltp_value > 0 else prev_close_value
            if current_price == 0:
                # FALLBACK: Default to face value when price data is missing
                current_price = 100.0  # Default to face value

            # Calculate current yield
            current_yield = calculate_current_yield(coupon_rate, current_price)
            current_yield_percent = current_yield * 100

            # Get yield change info
            pct_change = row.get("%CHNG", 0.0)
            try:
                pct_change_value = float(pct_change) if pd.notna(pct_change) else 0.0
            except (ValueError, TypeError):
                pct_change_value = 0.0

            yield_change_info = calculate_yield_change_info(pct_change_value)

            results.append(
                {
                    "isin": isin,
                    "name": bond_name,
                    "issuer": issuer,
                    "coupon_rate": coupon_rate,
                    "maturity_date": maturity_date,
                    "current_yield": current_yield,
                    "current_yield_percent": round(current_yield_percent, 2),
                    "yield_change": yield_change_info["yield_change"],
                    "yield_change_direction": yield_change_info[
                        "yield_change_direction"
                    ],
                }
            )
        except Exception:
            continue

    return SearchResponse(
        results=[BondSearchResult(**result) for result in results],
        total_results=len(results),
    )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "orchestrator_available": is_orchestrator_available()}


# ============= Chat Endpoint =============
# Orchestrator instance cache for chat endpoint
_chat_orchestrator = None
_chat_config = None


def _get_chat_orchestrator():
    """Get or create orchestrator instance for chat endpoint (similar to Streamlit app)"""
    global _chat_orchestrator, _chat_config

    if _chat_orchestrator is not None:
        return _chat_orchestrator, _chat_config

    import os
    import sys
    from pathlib import Path

    # Add bonds_agentic_sys to path (same as Streamlit app)
    project_root = Path(__file__).resolve().parent.parent / "app" / "bonds_agentic_sys"
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Import directly (not with app.bonds_agentic_sys prefix) since we added the path
    # from baschemas_v2 import SystemConfigV2
    # from orchestrator_v3 import create_orchestrator_v3

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, detail="OPENAI_API_KEY environment variable not set"
        )

    _chat_config = SystemConfigV2(
        openai_api_key=api_key,
        serpapi_key=os.getenv("SERPAPI_KEY"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        llm_temperature=0.0,
        rag_enabled=False,
        cache_enabled=True,
        enable_pathway_forecasts=False,
        enable_dynamic_model_selection=False,
        enable_guardrails=os.getenv("ENABLE_GUARDRAILS", "false").lower() == "true",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        guardrails_check_input=True,
        guardrails_check_output=True,
        valuation_weight=0.25,
        return_weight=0.30,
        quality_weight=0.25,
        liquidity_weight=0.20,
        portfolio_db_path=str(project_root / ".cache" / "portfolios"),
        cache_dir=str(project_root / ".cache"),
        vector_db_path=str(project_root / "vector_store"),
    )

    try:
        _chat_orchestrator = create_orchestrator_v3(_chat_config)
        return _chat_orchestrator, _chat_config
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize orchestrator: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat with the bond trading AI agent.

    This endpoint processes natural language queries about bonds, portfolios,
    and trading recommendations - similar to the Streamlit chat interface.

    Request Body:
    - prompt: User's question or request (required)
    - user_id: User identifier (default: "api_user")
    - thread_id: Thread ID for conversation history (optional)
    - conversation_history: Previous messages for context (optional)

    Returns:
    - success: Whether the query was processed successfully
    - response: AI generated response text
    - recommendations: Trade recommendations if any
    - processing_time: Time taken to process the query
    - has_analytics: Whether bond analytics data is available
    - has_scores: Whether bond scores are available
    - has_portfolio: Whether portfolio data is available
    - error: Error message if any

    Example queries:
    - "Find high yield AAA bonds with good liquidity"
    - "Recommend bonds to reduce my portfolio duration"
    - "What are the best PSU bonds for my portfolio?"
    - "Analyze my portfolio and suggest improvements"
    """
    import time

    start_time = time.time()

    try:
        # Get orchestrator
        orchestrator, config = _get_chat_orchestrator()

        # Generate thread_id if not provided
        thread_id = request.thread_id or f"{request.user_id}_api_session"

        # Run orchestrator
        state = await orchestrator.run_async(
            query=request.prompt,
            user_id=request.user_id,
            thread_id=thread_id,
            conversation_history=request.conversation_history,
        )

        # Extract response text
        if state.advisory and state.advisory.summary:
            response_text = state.advisory.summary
        elif state.advisory:
            response_text = "I've processed your query, but no response was generated. Please try rephrasing your question."
        else:
            response_text = (
                "I encountered an issue processing your query. Please try again."
            )

        # Extract recommendations
        recommendations = None
        if state.advisory and state.advisory.recommendations:
            recommendations = [
                RecommendationResponse(
                    action=rec.action,
                    name=rec.name,
                    isin=rec.isin,
                    rationale=rec.rationale,
                    expected_return=rec.expected_return,
                    confidence=rec.confidence,
                    risk_score=rec.risk_score,
                    quantity=rec.quantity if rec.quantity > 0 else None,
                    target_price=rec.target_price,
                )
                for rec in state.advisory.recommendations
            ]

        processing_time = time.time() - start_time

        return ChatResponse(
            success=True,
            response=response_text,
            recommendations=recommendations,
            processing_time=processing_time,
            has_analytics=bool(state.bond_analytics),
            has_scores=bool(state.bond_scores),
            has_portfolio=bool(state.portfolio),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        return ChatResponse(
            success=False,
            response="",
            recommendations=None,
            processing_time=processing_time,
            has_analytics=False,
            has_scores=False,
            has_portfolio=False,
            error=str(e),
        )
