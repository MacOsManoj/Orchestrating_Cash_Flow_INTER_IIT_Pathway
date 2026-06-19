"""
Bond Chat Recommendations Transformer
======================================

Transforms /api/bonds/chat POST response to BondTermsCard and BondPricingCard components.

Flow:
1. Extract the first ISIN from chat response recommendations
2. Fetch bond_details for that ISIN
3. Transform into one BondTermsCard and one BondPricingCard component

This transformer returns a list of 2 components (BondTermsCard + BondPricingCard) for the first recommended bond.
"""

import httpx
from typing import Dict, Any, List, Optional
import logging

from ..pipeline_registry import PIPELINE_ENDPOINTS, BACKEND_BASE_URL
from .bond_terms import transform_bond_terms
from .bond_pricing import transform_bond_pricing

logger = logging.getLogger(__name__)


async def fetch_bond_details(isin: str) -> Optional[Dict[str, Any]]:
    """
    Fetch bond details for a given ISIN.
    
    Args:
        isin: Bond ISIN identifier
        
    Returns:
        Bond details dict or None if failed
    """
    url = f"{BACKEND_BASE_URL}/api/bonds/{isin}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch bond details for {isin}: {e}")
        return None


async def transform_bond_chat_recommendations(
    api_response: Any,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Transform bonds chat response to bond component data for the first recommended bond.
    
    This transformer:
    1. Extracts the first ISIN from recommendations
    2. Fetches bond_details for that ISIN
    3. Returns list with one BondTermsCard and one BondPricingCard
    
    Args:
        api_response: Response from /api/bonds/chat POST endpoint (dict or nested dict)
        **kwargs: Additional parameters
        
    Returns:
        List of 2 component data dicts: [BondTermsCard, BondPricingCard]
    """
    # Handle nested response (if api_response is a dict with the chat response inside)
    if isinstance(api_response, dict):
        # Check if this is the chat response directly
        if "success" in api_response and "recommendations" in api_response:
            chat_response = api_response
        # Or if it's nested (e.g., {"chat": {...}})
        elif "chat" in api_response:
            chat_response = api_response["chat"]
        else:
            # Assume it's the chat response directly
            chat_response = api_response
    else:
        logger.warning("Invalid chat response format - expected dict")
        return []
    
    if not isinstance(chat_response, dict):
        logger.warning("Invalid chat response format")
        return []
    
    # Check if response is successful
    if not chat_response.get("success", False):
        logger.warning("Chat response indicates failure")
        return []
    
    # Extract recommendations
    recommendations = chat_response.get("recommendations", [])
    if not recommendations:
        logger.info("No recommendations in chat response")
        return []
    
    # Extract the first valid ISIN from recommendations
    first_isin = None
    first_recommendation = None
    for rec in recommendations:
        isin = rec.get("isin")
        if isin and isin.strip():
            first_isin = isin
            first_recommendation = rec
            break
    
    if not first_isin:
        logger.info("No valid ISIN found in recommendations")
        return []
    
    logger.info(f"Processing first recommended bond with ISIN: {first_isin}")
    
    # Fetch bond details for the first ISIN
    bond_details = await fetch_bond_details(first_isin)
    
    if not bond_details:
        logger.warning(f"Failed to fetch bond details for {first_isin}")
        return []
    
    # Build component data for the first bond
    components = []
    
    # Transform to BondTermsCard
    terms_data = transform_bond_terms(bond_details)
    components.append({
        "type": "BondTermsCard",
        "data": terms_data
    })
    
    # Transform to BondPricingCard
    pricing_data = transform_bond_pricing(bond_details)
    components.append({
        "type": "BondPricingCard",
        "data": pricing_data
    })
    
    logger.info(f"Created BondTermsCard and BondPricingCard for ISIN {first_isin}")
    return components


# Export the async version as the main transformer
# The orchestrator will detect it's async and await it
transform_bond_chat_recommendations = transform_bond_chat_recommendations

