"""
CashFlow Table Transformer
===========================

Transforms /api/cashflow/inandoutflow response to comp-17 (CashFlowTable) format.

API Response (from cashflow_router.py - returns pandas JSON with orient='index'):
The endpoint returns analyze_last_28_days which is a pivot table with:
- Index: categories (Total Deposit, Job Income, Interest, Loans, Online Withdrawal, Offline Withdrawal)
- Columns: week buckets (Last Week, Second Last Week, Third Last Week, Fourth Last Week)

Example response:
{
    "Total Deposit": {"Last Week": 1000, "Second Last Week": 500, ...},
    "Job Income": {"Last Week": 2000, ...},
    "Interest": {"Last Week": 100, ...},
    "Loans": {"Last Week": 500, ...},
    "Online Withdrawal": {"Last Week": 300, ...},
    "Offline Withdrawal": {"Last Week": 200, ...}
}

Component Format:
{
    "rows": [
        {
            "date": "Last Week",
            "openingBalance": "₹0",
            "inflows": 3100,  # Total Deposit + Job Income + Interest
            "outflows": 1000,  # Loans + Online Withdrawal + Offline Withdrawal
            "netCashFlow": 2100,
            "endingBalance": "₹2,100",
            "lcrPercentage": 0
        },
        ...
    ]
}
"""

from typing import Dict, Any, List
import json


def _format_currency(value: float) -> str:
    """Format a number as INR currency string."""
    if abs(value) >= 10000000:  # 1 Cr+
        return f"₹{value/10000000:.2f} Cr"
    elif abs(value) >= 100000:  # 1 Lakh+
        return f"₹{value/100000:.2f} L"
    else:
        return f"₹{value:,.0f}"


def _safe_float(val) -> float:
    """Safely convert a value to float."""
    try:
        if val is None:
            return 0.0
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def transform_cashflow_table(api_response: Any, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
    """
    Transform cashflow/inandoutflow API response to CashFlowTable component format.
    
    Args:
        api_response: Response from /api/cashflow/inandoutflow
                     This is a JSON string from pandas to_json(orient='index')
                     containing weekly category summaries
        **kwargs: Additional parameters
    
    Returns:
        Component-ready JSON with rows array
    """
    # Handle JSON string response (from pandas to_json)
    if isinstance(api_response, str):
        try:
            api_response = json.loads(api_response)
        except json.JSONDecodeError:
            return {"rows": [_create_empty_row()]}
    
    # Check if it's the pivot table format (orient='index')
    # Keys would be category names like "Total Deposit", "Job Income", etc.
    inflow_categories = ["Total Deposit", "Job Income", "Interest"]
    outflow_categories = ["Loans", "Online Withdrawal", "Offline Withdrawal"]
    
    if isinstance(api_response, dict) and any(cat in api_response for cat in inflow_categories + outflow_categories):
        return _transform_pivot_format(api_response, inflow_categories, outflow_categories)
    
    # Handle list of records (legacy/alternate format)
    if isinstance(api_response, list):
        return _transform_records_format(api_response)
    
    # Handle dict with data/rows key
    if isinstance(api_response, dict):
        records = api_response.get("data", api_response.get("rows", []))
        if isinstance(records, list):
            return _transform_records_format(records)
    
    # Fallback: return empty row
    return {"rows": [_create_empty_row()]}


def _create_empty_row(date: str = "") -> Dict[str, Any]:
    """Create an empty row with default values."""
    return {
        "date": date,
        "openingBalance": "₹0",
        "inflows": 0.0,
        "outflows": 0.0,
        "netCashFlow": 0.0,
        "endingBalance": "₹0",
        "lcrPercentage": 0.0
    }


def _transform_pivot_format(
    data: Dict[str, Dict[str, float]], 
    inflow_cats: List[str], 
    outflow_cats: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Transform pivot table format (orient='index') to CashFlowTable rows.
    
    Each week becomes a row with aggregated inflows and outflows.
    """
    # Get all week names from the data
    week_names = []
    for cat_data in data.values():
        if isinstance(cat_data, dict):
            week_names = list(cat_data.keys())
            break
    
    if not week_names:
        return {"rows": [_create_empty_row()]}
    
    # Desired order (most recent first)
    ordered_weeks = ["Last Week", "Second Last Week", "Third Last Week", "Fourth Last Week"]
    week_names = [w for w in ordered_weeks if w in week_names] or week_names
    
    rows = []
    running_balance = 0.0
    
    # Process in reverse order (oldest first) to calculate running balance
    for week in reversed(week_names):
        # Sum inflows
        inflows = 0.0
        for cat in inflow_cats:
            if cat in data and isinstance(data[cat], dict):
                inflows += _safe_float(data[cat].get(week, 0))
        
        # Sum outflows
        outflows = 0.0
        for cat in outflow_cats:
            if cat in data and isinstance(data[cat], dict):
                outflows += _safe_float(data[cat].get(week, 0))
        
        net = inflows - outflows
        opening = running_balance
        closing = opening + net
        running_balance = closing
        
        # Calculate simple LCR approximation (if we have outflows)
        lcr = (closing / outflows * 100) if outflows > 0 else 0.0
        
        rows.append({
            "date": week,
            "openingBalance": _format_currency(opening),
            "inflows": round(inflows, 2),
            "outflows": round(outflows, 2),
            "netCashFlow": round(net, 2),
            "endingBalance": _format_currency(closing),
            "lcrPercentage": round(lcr, 1)
        })
    
    # Reverse to show most recent first
    rows.reverse()
    
    return {"rows": rows}


def _transform_records_format(records: List[Dict]) -> Dict[str, List[Dict[str, Any]]]:
    """Transform list of records format to CashFlowTable rows."""
    if not records:
        return {"rows": [_create_empty_row()]}
    
    rows = []
    for record in records:
        # Handle various field name formats (snake_case, camelCase, Title_Case)
        date = (
            record.get("Date") or 
            record.get("date") or 
            ""
        )
        
        opening = _safe_float(
            record.get("Opening_Balance") or 
            record.get("openingBalance") or 
            record.get("opening_balance") or 
            0.0
        )
        
        inflows = _safe_float(
            record.get("Total_Inflows") or 
            record.get("inflows") or 
            record.get("total_inflows") or 
            0.0
        )
        
        outflows = _safe_float(
            record.get("Total_Outflows") or 
            record.get("outflows") or 
            record.get("total_outflows") or 
            0.0
        )
        
        net = _safe_float(
            record.get("Net_Cashflow") or 
            record.get("netCashFlow") or 
            record.get("net_cashflow") or 
            record.get("net-cash-flow") or 
            0.0
        )
        
        closing = _safe_float(
            record.get("Closing_Balance") or 
            record.get("endingBalance") or 
            record.get("closing_balance") or 
            0.0
        )
        
        lcr = _safe_float(
            record.get("LCR") or 
            record.get("lcrPercentage") or 
            record.get("lcr") or 
            0.0
        )
        
        rows.append({
            "date": date,
            "openingBalance": _format_currency(opening),
            "inflows": round(inflows, 2),
            "outflows": round(outflows, 2),
            "netCashFlow": round(net, 2),
            "endingBalance": _format_currency(closing),
            "lcrPercentage": round(lcr, 1)
        })
    
    return {"rows": rows}
