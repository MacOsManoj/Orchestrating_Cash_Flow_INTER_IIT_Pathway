"""
Fundamentals Card Transformer
==============================

Transforms /api/stocks/agent/query response to comp-11 (FundamentalsCard) format.
Extracts fundamental_agent and technical_output from the full analysis response.

API Response (sample_output.json):
{
    "ticker": ["RELIANCE"],
    "fundamental_output": {
        "analyses": {
            "RELIANCE": {
                "current_financials_fy": {
                    "fiscal_year": "2025",
                    "revenue_cr": 980136.0,
                    "ebitda_cr": 165718.0,
                    "net_income_cr": 69648.0,
                    "fcf_cr": 38736.0,
                    "pe_ratio": 22.21
                },
                "analysis_summary": {...},
                ...
            }
        }
    },
    "technical_output": {
        "ticker": "RELIANCE",
        "signal": "HOLD",
        "strength": 0.0,
        "reason": "...",
        ...
    }
}

Component Format:
{
    "companyName": str,
    "fundamentals": [
        {"label": str, "value": str/number}
    ],
    "technical": [
        {"label": str, "value": str/number}
    ]
}
"""

from typing import Dict, Any, List


def transform_fundamentals_card(api_response: Any, **kwargs) -> Dict[str, Any]:
    """
    Transform stocks /query POST API response to FundamentalsCard component format.
    
    The stock agent response has data nested under 'response' key:
    {
        "success": true,
        "ticker": "RELIANCE",
        "response": {
            "fundamental_output": {...},
            "technical_output": {...},
            ...
        }
    }
    
    Args:
        api_response: Full analysis response from POST /query
        **kwargs: ticker param may be passed
    
    Returns:
        Component-ready JSON with company fundamentals and technicals
    """
    if not isinstance(api_response, dict):
        return {
            "companyName": "Unknown",
            "fundamentals": [],
            "technical": []
        }
    
    # Handle nested response structure (stock agent wraps data in 'response' key)
    response_data = api_response.get("response", api_response)
    
    # Get ticker from response or kwargs
    ticker = kwargs.get("ticker") or api_response.get("ticker", "Unknown")
    # Also try to get from tickers array in nested response
    tickers = response_data.get("tickers", [])
    if tickers and not kwargs.get("ticker"):
        ticker = tickers[0]
    
    # Extract fundamental data
    fundamental_output = response_data.get("fundamental_output", {})
    
    # Handle different response structures
    # Structure 1: Direct ticker data under fundamental_output
    # Structure 2: Nested under 'analyses' key
    analyses = fundamental_output.get("analyses", {})
    if analyses:
        ticker_data = analyses.get(ticker, {})
    else:
        # Direct structure - try ticker as key
        ticker_data = fundamental_output.get(ticker, fundamental_output)
    
    financials = ticker_data.get("current_financials_fy", {})
    analysis_summary = ticker_data.get("analysis_summary", {})
    
    fundamentals = []
    
    # Add fiscal year
    if financials.get("fiscal_year"):
        fundamentals.append({
            "label": "Fiscal Year",
            "value": financials["fiscal_year"]
        })
    
    # Add revenue (in Cr INR)
    if financials.get("revenue_cr"):
        fundamentals.append({
            "label": "Revenue",
            "value": f"₹{financials['revenue_cr']:,.0f} Cr"
        })
    
    # Add EBITDA
    if financials.get("ebitda_cr"):
        fundamentals.append({
            "label": "EBITDA",
            "value": f"₹{financials['ebitda_cr']:,.0f} Cr"
        })
    
    # Add Net Income
    if financials.get("net_income_cr"):
        fundamentals.append({
            "label": "Net Income",
            "value": f"₹{financials['net_income_cr']:,.0f} Cr"
        })
    
    # Add Free Cash Flow
    if financials.get("fcf_cr"):
        fundamentals.append({
            "label": "Free Cash Flow",
            "value": f"₹{financials['fcf_cr']:,.0f} Cr"
        })
    
    # Add P/E Ratio
    if financials.get("pe_ratio"):
        fundamentals.append({
            "label": "P/E Ratio",
            "value": round(financials["pe_ratio"], 2)
        })
    
    # Add recommendation
    if analysis_summary.get("recommendation"):
        fundamentals.append({
            "label": "Recommendation",
            "value": analysis_summary["recommendation"]
        })
    
    # Extract technical data (also from nested response)
    technical_output = response_data.get("technical_output", {})
    
    technical = []
    
    # Add signal
    if technical_output.get("signal"):
        technical.append({
            "label": "Signal",
            "value": technical_output["signal"]
        })
    
    # Add signal strength
    if technical_output.get("strength") is not None:
        technical.append({
            "label": "Signal Strength",
            "value": f"{technical_output['strength']:.1%}" if isinstance(technical_output['strength'], float) else technical_output['strength']
        })
    
    # Add reason
    if technical_output.get("reason"):
        # Clean up the reason text
        reason = technical_output["reason"]
        if reason.startswith("[CALCULATED] "):
            reason = reason.replace("[CALCULATED] ", "")
        technical.append({
            "label": "Analysis",
            "value": reason
        })
    
    return {
        "companyName": ticker,
        "fundamentals": fundamentals,
        "technical": technical
    }
