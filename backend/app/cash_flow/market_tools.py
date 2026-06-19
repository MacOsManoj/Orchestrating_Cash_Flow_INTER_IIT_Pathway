import calendar
import io
import os
import re
import requests
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from nsetools import Nse
from nsepython import nse_fiidii, nse_get_advances_declines
from typing import Dict, Optional

import pdfplumber

from asyncio import all_tasks
import requests
from bs4 import BeautifulSoup
import re

NUM_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]+")


def get(url: str) -> str:
    """Fetch HTML content from a URL"""
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text


def parse_number(s: str):
    """Parse a string into a float number"""
    if not s:
        return None
    s = s.strip().replace(",", "")
    m = NUM_RE.search(s)
    if not m:
        return None
    return float(m.group(0))


def parse_percent(s: str):
    """Parse a percentage string into float"""
    if not s:
        return None
    s = s.strip().replace("%", "")
    return parse_number(s)


def find_table(soup: BeautifulSoup):
    """Find the bonds table by looking for 'Bonds' and 'Yield' headers"""
    for table in soup.find_all("table"):
        th = [t.get_text(strip=True).lower() for t in table.find_all("th")]
        if "bonds" in th and "yield" in th:
            return table
    return None


def extract_rows(table: BeautifulSoup):
    """Extract rows of bond data from a table"""
    rows = []
    for tr in table.find_all("tr"):
        if tr.find("th"):  # skip header
            continue

        tds = tr.find_all("td")
        if not tds:
            continue

        data = {}
        data["Bonds"] = tds[0].get_text(strip=True)
        data["Yield"] = (
            parse_number(tds[1].get_text(strip=True)) if len(tds) > 1 else None
        )
        data["Day"] = (
            parse_percent(tds[3].get_text(strip=True)) if len(tds) > 3 else None
        )
        data["Month"] = (
            parse_percent(tds[4].get_text(strip=True)) if len(tds) > 4 else None
        )
        data["Year"] = (
            parse_percent(tds[5].get_text(strip=True)) if len(tds) > 5 else None
        )
        data["Date"] = tds[6].get_text(strip=True) if len(tds) > 6 else None

        rows.append(data)
    return rows


all_sector_data = {
    "IT": "NIFTY IT",
    "BANK": "NIFTY BANK",
    "FINANCE": "NIFTY FIN SERVICE",
    "FMCG": "NIFTY FMCG",
    "AUTO": "NIFTY AUTO",
    "METAL": "NIFTY METAL",
    "MEDIA": "NIFTY MEDIA",
    "PHARMA": "NIFTY PHARMA",
    "PSU BANK": "NIFTY PSU BANK",
    "PVT BANK": "NIFTY PVT BANK",
    "REALTY": "NIFTY REALTY",
    "HEALTHCARE": "NIFTY HEALTHCARE",
    "OIL AND GAS": "NIFTY OIL AND GAS",
    "OIL & GAS": "NIFTY OIL AND GAS",
}

# Pre-defined constituent lists
NIFTY50_CONSTITUENTS = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "BAJFINANCE",
    "HCLTECH",
    "SUNPHARMA",
    "TITAN",
    "ULTRACEMCO",
    "NESTLEIND",
    "WIPRO",
    "ADANIPORTS",
    "ONGC",
    "NTPC",
    "POWERGRID",
    "BAJAJFINSV",
    "M&M",
    "TATASTEEL",
    "TECHM",
    "JSWSTEEL",
    "INDUSINDBK",
    "COALINDIA",
    "DRREDDY",
    "BRITANNIA",
    "GRASIM",
    "CIPLA",
    "EICHERMOT",
    "HINDALCO",
    "HEROMOTOCO",
    "DIVISLAB",
    "TATACONSUM",
    "APOLLOHOSP",
    "BAJAJ-AUTO",
    "SHREECEM",
    "ADANIENT",
    "TATAMOTORS",
    "UPL",
    "SBILIFE",
    "BPCL",
    "HDFCLIFE",
]

BANKNIFTY_CONSTITUENTS = [
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "KOTAKBANK",
    "AXISBANK",
    "INDUSINDBK",
    "BANDHANBNK",
    "FEDERALBNK",
    "IDFCFIRSTB",
    "PNB",
    "BANKBARODA",
    "AUBANK",
]

try:
    from nsepython import option_chain
except ImportError:
    from nsepythonserver import option_chain

try:
    from nsepy import index_pe_pb_div
except:
    from nsepythonserver import index_pe_pb_div


def get_stock_indices(stock_index: str) -> str:
    """Get the stock indices for the given stock index.

    This function retrieves real-time information about major Indian stock market indices
    using Yahoo Finance API. The function supports the following indexes:

    - NIFTY50: The Nifty 50 index (^NSEI) represents the weighted average of 50 of the
      largest Indian companies listed on the National Stock Exchange (NSE). It is one of
      the two main stock indices used in India, the other being the BSE SENSEX. NIFTY50
      is widely used as a benchmark for the Indian equity market and covers major sectors
      of the Indian economy.

    - SENSEX30: The S&P BSE SENSEX (^BSESN) is a free-float market-weighted stock market
      index of 30 well-established and financially sound companies listed on the Bombay
      Stock Exchange (BSE). It is the oldest stock index in India and serves as a
      barometer of the Indian economy.

    - BANKNIFTY: The Nifty Bank index (^NSEBANK) represents the most liquid and large
      capitalized Indian banking stocks. It provides investors with a benchmark that
      captures the capital market performance of Indian bank stocks.

    Args:
        stock_index (str): The name of the stock index. Must be one of: "NIFTY50",
                          "SENSEX30", or "BANKNIFTY".

    Returns:
        str: A dictionary containing detailed information about the requested stock index
             (including current price, market data, company information, etc.) if a valid
             index is provided. Returns "Invalid stock index" if an unsupported index
             name is provided.
    """
    if stock_index == "NIFTY50":
        return yf.Ticker("^NSEI").info
    elif stock_index == "SENSEX30":
        return yf.Ticker("^BSESN").info
    elif stock_index == "BANKNIFTY":
        return yf.Ticker("^NSEBANK").info
    else:
        return "Invalid stock index"


def get_forex_performance(
    from_currency: str, to_currency: str, period: str = "1mo", interval: str = "1d"
) -> str:
    """
    Fetch forex data for a given time period and return a performance summary.

    This function provides:
        - Latest price
        - Opening price of the selected period
        - Highest price in the period
        - Lowest price in the period
        - Percentage price change over the period
        - Z-score of the latest price relative to the prices in the period
        - MA20 (20-period Moving Average) based on the selected interval

    Args:
        from_currency (str): Base currency (e.g., "USD").
        to_currency (str): Quote currency (e.g., "INR").
        period (str): Time duration (e.g., "1d", "5d", "1mo", "3mo", "1y", "ytd", "max").
        interval (str): Candle interval (e.g., "1m", "5m", "15m", "1h", "1d", "1wk", "1mo").

    Returns:
        str: Formatted text summary.
    """
    ticker = f"{from_currency.upper()}{to_currency.upper()}=X"
    data = yf.Ticker(ticker).history(period=period, interval=interval)

    if data.empty:
        return f"No forex data available for {from_currency}/{to_currency}."

    # Required price metrics
    opening_price = float(data["Open"].iloc[0])
    latest_price = float(data["Close"].iloc[-1])
    highest_price = float(data["High"].max())
    lowest_price = float(data["Low"].min())

    # Percentage change
    pct_change = ((latest_price - opening_price) / opening_price) * 100

    # Z-score computation
    prices = data["Close"].to_numpy()
    mean_price = np.mean(prices)
    std_price = np.std(prices)
    zscore = (latest_price - mean_price) / std_price if std_price != 0 else 0.0

    # MA20 (20-period moving average)
    ma20 = data["Close"].rolling(window=20).mean().iloc[-1]
    ma20_text = f"{ma20:.4f}" if not np.isnan(ma20) else "Not enough data"

    summary = (
        f"{from_currency.upper()} → {to_currency.upper()} Forex Report\n"
        f"Period: {period} | Interval: {interval}\n\n"
        f"Latest price: {latest_price:.4f}\n"
        f"Opening price: {opening_price:.4f}\n"
        f"Highest price in period: {highest_price:.4f}\n"
        f"Lowest price in period: {lowest_price:.4f}\n"
        f"Percentage change: {pct_change:.2f}%\n"
        f"Z-score of latest price: {zscore:.3f}\n"
        f"MA20 (20-period Moving Average): {ma20_text}\n"
    )
    return summary


def get_commodity_performance(commodity: str) -> str:
    """
    Fetch 1-month commodity performance using a clean commodity name (not natural sentences).

    Acceptable input strings (must match exactly):
        "gold", "silver", "crude oil wti", "wti",
        "crude oil brent", "brent", "natural gas",
        "natural gas futures", "copper", "wheat",
        "corn", "platinum", "palladium"
    """

    # Load environment variables and get API key
    load_dotenv()
    api_key = os.getenv("COMMODITY_API_KEY")

    if not api_key:
        return "❌ API key not found. Make sure COMMODITY-API-KEY is set in your .env file."

    mapping = {
        "gold": "XAU",
        "silver": "XAG",
        "crude oil wti": "WTIOIL-SPOT",
        "wti": "WTIOIL-SPOT",
        "crude oil brent": "BRENTOIL-FUT",
        "brent": "BRENTOIL-FUT",
        "natural gas": "NG-FUT",
        "natural gas futures": "NG-FUT",
        "copper": "HG-SPOT",
        "wheat": "ZW-SPOT",
        "corn": "CORN",
        "platinum": "PL",
        "palladium": "PA",
    }

    key = commodity.lower().strip()
    if key not in mapping:
        return "Invalid commodity. Try: gold, silver, crude oil wti, brent, natural gas, copper..."

    symbol = mapping[key]

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=30)

    url = (
        f"https://api.commoditypriceapi.com/v2/rates/time-series"
        f"?symbols={symbol}&startDate={start_date}&endDate={end_date}"
    )
    res = requests.get(url, headers={"x-api-key": api_key})

    if res.status_code != 200:
        return f"API Error {res.status_code}: {res.text}"

    data = res.json()
    rates = data.get("rates", {})
    if not rates:
        return "No price data found for this commodity."

    opens, highs, lows, closes = [], [], [], []

    for _, values in sorted(rates.items()):
        if symbol in values:
            rec = values[symbol]
            opens.append(rec["open"])
            highs.append(rec["high"])
            lows.append(rec["low"])
            closes.append(rec["close"])

    opening_price = opens[0]
    latest_price = closes[-1]
    highest_price = max(highs)
    lowest_price = min(lows)

    ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
    pct_change = ((latest_price - opening_price) / opening_price) * 100

    mean_price = np.mean(closes)
    std_price = np.std(closes)
    zscore = (latest_price - mean_price) / std_price if std_price > 0 else 0.0

    return (
        f"Commodity: {symbol}\n"
        f"Period: Last 1 Month\n\n"
        f"Latest price: {latest_price:.2f}\n"
        f"Opening price: {opening_price:.2f}\n"
        f"Highest price in period: {highest_price:.2f}\n"
        f"Lowest price in period: {lowest_price:.2f}\n\n"
        f"MA20: {ma20:.2f}\n"
        f"% Change (open → latest): {pct_change:.2f}%\n"
        f"Z-score of latest price: {zscore:.3f}\n"
    )


def get_bond_yields(
    url: str = "https://tradingeconomics.com/india/government-bond-yield",
) -> list:
    """Get Indian government bond yield data from Trading Economics.

    Args:
        url (str, optional): Trading Economics bond yield page URL. Defaults to India
                           government bond yield page.

    Returns:
        list: List of dictionaries, each containing bond yield data:
              - "Bonds" (str): Bond name/maturity (e.g., "India 10Y", "India 52W", "India 2Y")
              - "Yield" (float): Current yield percentage (e.g., 6.52 for 6.52%)
              - "Day" (float): Day-over-day yield change in percentage points (e.g., 0.011)
              - "Month" (float): Month-over-month yield change in percentage points (e.g., -0.018)
              - "Year" (float): Year-over-year yield change in percentage points (e.g., -0.315)
              - "Date" (str): Last updated date in "MMM/DD" format (e.g., "Nov/28")

    Raises:
        ValueError: If no bond yield table is found on the page.
        requests.exceptions.RequestException: If webpage fetch fails.
    """
    html = get(url)
    soup = BeautifulSoup(html, "lxml")
    table = find_table(soup)
    if not table:
        raise ValueError("No matching table found on the page.")
    return extract_rows(table)


def get_sector_info(sector_name: str):
    """
    Tool: get_sector_info

    Description:
        This tool provides complete live sector index data from NSE using the nsetools package.
        Provide a sector name (exact name or alias) and it returns full sector information.

        Supported sector indices:
            - NIFTY AUTO
            - NIFTY BANK
            - NIFTY FIN SERVICE
            - NIFTY FMCG
            - NIFTY IT
            - NIFTY MEDIA
            - NIFTY METAL
            - NIFTY PHARMA
            - NIFTY PSU BANK
            - NIFTY PVT BANK
            - NIFTY REALTY
            - NIFTY HEALTHCARE
            - NIFTY OIL AND GAS

        Example Inputs:
            get_sector("NIFTY IT")
            get_sector("IT")
            get_sector("bank")
            get_sector("Pharma")
    """

    # create instance inside the function
    nse = Nse()

    # alias map inside the function
    SECTOR_MAP = all_sector_data

    # normalize input
    name = sector_name.strip().upper()

    # alias lookup
    if name in SECTOR_MAP:
        name = SECTOR_MAP[name]

    try:
        data = nse.get_index_quote(name)
        if not data:
            return {"error": f"Sector '{sector_name}' not found"}
        return data
    except Exception as e:
        return {"error": str(e)}


def get_india_vix(period: str = "1mo") -> dict:
    """
    Get India VIX (Volatility Index) data and analysis.

    India VIX represents the expected volatility in NIFTY 50 over the next 30 days,
    expressed as an annualized percentage. It's calculated from NIFTY options prices.

    Interpretation:
        - Higher VIX = Higher expected market volatility/risk
        - Lower VIX = Calmer, more stable market conditions
        - Normal range: 15-35
        - Below 15: Low volatility (complacent market)
        - Above 35: High volatility (fearful market)
        - All-time high: ~87 (March 2020 COVID crash)

    Args:
        period (str): Time period for historical context.
                     Options: "1d", "5d", "1mo", "3mo", "6mo", "1y", "ytd", "max"
                     Default: "1mo"

    Returns:
        dict: Dictionary containing:
            - current_vix: Latest VIX value
            - previous_close: Previous day's close
            - day_change: Change from previous close
            - day_change_pct: Percentage change from previous close
            - period_high: Highest VIX in the period
            - period_low: Lowest VIX in the period
            - period_avg: Average VIX in the period
            - zscore: Z-score of current VIX (std devs from mean)
            - volatility_regime: Text classification (Low/Normal/High/Extreme)
            - market_signal: Interpretation for allocation decisions
            - last_updated: Timestamp of data
    """
    ticker = yf.Ticker("^INDIAVIX")
    hist = ticker.history(period=period)

    if hist.empty:
        return {"error": "Unable to fetch India VIX data"}

    # Current metrics
    current_vix = float(hist["Close"].iloc[-1])
    previous_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_vix
    day_change = current_vix - previous_close
    day_change_pct = (day_change / previous_close) * 100 if previous_close != 0 else 0

    # Period statistics
    period_high = float(hist["High"].max())
    period_low = float(hist["Low"].min())
    period_avg = float(hist["Close"].mean())
    period_std = float(hist["Close"].std())

    # Z-score calculation
    zscore = (current_vix - period_avg) / period_std if period_std != 0 else 0

    # Volatility regime classification
    if current_vix < 15:
        regime = "Low Volatility"
        signal = "Complacent market - consider reducing exposure or hedging"
    elif current_vix < 25:
        regime = "Normal Volatility"
        signal = "Stable conditions - normal allocation strategies"
    elif current_vix < 35:
        regime = "Elevated Volatility"
        signal = "Increased uncertainty - reduce leverage, wider stops"
    else:
        regime = "High Volatility"
        signal = "High fear/uncertainty - opportunities for contrarian plays"

    return {
        "current_vix": round(current_vix, 2),
        "previous_close": round(previous_close, 2),
        "day_change": round(day_change, 2),
        "day_change_pct": round(day_change_pct, 2),
        "period_high": round(period_high, 2),
        "period_low": round(period_low, 2),
        "period_avg": round(period_avg, 2),
        "zscore": round(zscore, 2),
        "volatility_regime": regime,
        "market_signal": signal,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_fii_dii_via_nsepython() -> dict:
    """
    Get FII/DII data from NSE using nsepython library.
    """
    return nse_fiidii(mode="raw")


def get_advance_decline_analysis(category: str = "all") -> Dict:
    """
    Get advance/decline analysis for specified category.

    Args:
        category (str): "all", "nifty50", or "banknifty"

    Returns:
        dict: Advance/decline metrics
    """
    try:
        df = nse_get_advances_declines()

        if df.empty:
            return {"error": "Unable to fetch data"}

        # Determine category
        category_lower = category.lower().strip()

        if category_lower in ["nifty50", "nifty"]:
            symbol_list = NIFTY50_CONSTITUENTS
            category_name = "NIFTY 50"
        elif category_lower in ["banknifty", "bank"]:
            symbol_list = BANKNIFTY_CONSTITUENTS
            category_name = "BANK NIFTY"
        else:
            symbol_list = None
            category_name = "Overall Market"

        # Filter data
        if symbol_list:
            df_filtered = df[df["symbol"].isin(symbol_list)].copy()
        else:
            df_filtered = df.copy()

        # Calculate metrics
        advances = len(df_filtered[df_filtered["pChange"] > 0])
        declines = len(df_filtered[df_filtered["pChange"] < 0])
        unchanged = len(df_filtered[df_filtered["pChange"] == 0])
        total = len(df_filtered)

        ad_ratio = advances / declines if declines > 0 else float("inf")
        net_advances = advances - declines

        # Volume metrics
        advancing_volume = df_filtered[df_filtered["pChange"] > 0][
            "totalTradedVolume"
        ].sum()
        declining_volume = df_filtered[df_filtered["pChange"] < 0][
            "totalTradedVolume"
        ].sum()
        volume_ratio = (
            advancing_volume / declining_volume
            if declining_volume > 0
            else float("inf")
        )

        # 52-week extremes
        near_52w_high = len(df_filtered[df_filtered["nearWKH"] == True])
        near_52w_low = len(df_filtered[df_filtered["nearWKL"] == True])

        return {
            "category": category_name,
            "total_stocks": total,
            "advances": advances,
            "declines": declines,
            "unchanged": unchanged,
            "ad_ratio": round(ad_ratio, 2) if ad_ratio != float("inf") else None,
            "net_advances": net_advances,
            "pct_advancing": round((advances / total * 100), 1) if total > 0 else 0,
            "pct_declining": round((declines / total * 100), 1) if total > 0 else 0,
            "volume_ratio": round(volume_ratio, 2)
            if volume_ratio != float("inf")
            else None,
            "near_52w_high": near_52w_high,
            "near_52w_low": near_52w_low,
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {"error": str(e)}


def get_india_pmi_data(sector: str = "both") -> str:
    """
    Fetch India's Purchasing Managers' Index (PMI) for Manufacturing and/or Services sectors.

    PMI is a leading economic indicator measuring business activity. Above 50 = expansion,
    below 50 = contraction. Data from S&P Global, published monthly (first week of month).

    PMI Components: New Orders (30%), Output (25%), Employment (20%),
                   Suppliers' Delivery Times (15%), Stock of Purchases (10%)

    Use Cases:
    - Leading indicator for GDP growth (predicts 1-2 months ahead)
    - Shows business sentiment and economic direction
    - Manufacturing PMI correlates with industrial production
    - Services PMI indicates consumer demand strength

    Args:
        sector (str): "manufacturing", "services", or "both" (default)

    Returns:
        str: Formatted summary with latest PMI, change from previous month,
             long-run average, historical extremes, and economic interpretation

    Raises:
        Exception: If data fetching fails
    """

    def fetch_pmi(url: str, sector_name: str) -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text()

        current_pattern = r"(\d+\.\d+)\s+points\s+in\s+(\w+)\s+from\s+(\d+\.\d+)\s+points\s+in\s+(\w+)"
        avg_pattern = r"averaged\s+(\d+\.\d+)\s+points"
        high_pattern = (
            r"all time high of\s+(\d+\.\d+)\s+points\s+in\s+(\w+)\s+of\s+(\d+)"
        )
        low_pattern = r"record low of\s+(\d+\.\d+)\s+points\s+in\s+(\w+)\s+of\s+(\d+)"

        current = re.search(current_pattern, text)
        if not current:
            raise Exception(f"Failed to extract {sector_name} PMI data")

        return {
            "sector": sector_name,
            "latest": float(current.group(1)),
            "latest_month": current.group(2),
            "previous": float(current.group(3)),
            "previous_month": current.group(4),
            "avg": float(re.search(avg_pattern, text).group(1))
            if re.search(avg_pattern, text)
            else None,
            "high": float(re.search(high_pattern, text).group(1))
            if re.search(high_pattern, text)
            else None,
            "high_date": f"{re.search(high_pattern, text).group(2)} {re.search(high_pattern, text).group(3)}"
            if re.search(high_pattern, text)
            else None,
            "low": float(re.search(low_pattern, text).group(1))
            if re.search(low_pattern, text)
            else None,
            "low_date": f"{re.search(low_pattern, text).group(2)} {re.search(low_pattern, text).group(3)}"
            if re.search(low_pattern, text)
            else None,
        }

    urls = {
        "manufacturing": "https://tradingeconomics.com/india/manufacturing-pmi",
        "services": "https://tradingeconomics.com/india/services-pmi",
    }

    results = {}
    if sector.lower() in ["manufacturing", "both"]:
        results["manufacturing"] = fetch_pmi(urls["manufacturing"], "Manufacturing")
    if sector.lower() in ["services", "both"]:
        results["services"] = fetch_pmi(urls["services"], "Services")

    output = [
        f"INDIA PMI REPORT | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}\n"
    ]

    for key, data in results.items():
        change = data["latest"] - data["previous"]
        status = (
            "EXPANSION"
            if data["latest"] > 50
            else "CONTRACTION"
            if data["latest"] < 50
            else "NO CHANGE"
        )
        strength = "Strong" if abs(data["latest"] - 50) > 5 else "Moderate"
        vs_avg = data["latest"] - data["avg"] if data["avg"] else 0

        output.append(f"\n{data['sector'].upper()} SECTOR")
        output.append(
            f"Latest ({data['latest_month']} 2025): {data['latest']:.2f} | {status} ({strength})"
        )
        output.append(
            f"Previous ({data['previous_month']}): {data['previous']:.2f} | Change: {change:+.2f}"
        )

        if data["avg"]:
            output.append(
                f"Long-run Average (2012-2025): {data['avg']:.2f} | Current vs Avg: {vs_avg:+.2f}"
            )

        if data["high"] and data["low"]:
            output.append(
                f"Historical Range: {data['low']:.2f} ({data['low_date']}) to {data['high']:.2f} ({data['high_date']})"
            )

        if data["latest"] > 55:
            output.append("Signal: Strong expansion means Positive for economic growth")
        elif data["latest"] > 50:
            output.append("Signal: Moderate expansion means Softening momentum")
        elif data["latest"] > 45:
            output.append("Signal: Mild contraction means Economic slowdown warning")
        else:
            output.append("Signal: Severe contraction means Recessionary conditions")

    output.append(f"PMI Scale: >50=Expansion, <50=Contraction")

    return "\n".join(output)


def get_india_inflation_data(indicator: str = "both") -> str:
    """
    Fetch India's Consumer Price Index (CPI) and Wholesale Price Index (WPI) inflation data.

    CPI measures retail-level inflation (what consumers pay). WPI measures wholesale-level
    inflation (producer prices). Both are key indicators for RBI monetary policy decisions.

    Use Cases:
    - CPI directly impacts interest rate decisions by RBI
    - High CPI (>6%) triggers monetary tightening
    - WPI predicts future CPI trends (1-2 month lag)
    - Food inflation in CPI affects rural purchasing power
    - Combined view shows complete inflation picture

    Args:
        indicator (str): "cpi", "wpi", or "both" (default)

    Returns:
        str: Formatted summary with latest inflation rates, MoM/YoY changes,
             sector-wise breakdown, and policy implications

    Raises:
        Exception: If data fetching fails
    """

    def fetch_cpi_data() -> dict:
        """Fetch CPI from Trading Economics"""
        url = "https://tradingeconomics.com/india/inflation-cpi"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10, verify=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text()

        # Pattern
        cpi_pattern = r"(?:fell|rose|decreased|increased)\s+to\s+([0-9.]+)%\s+in\s+(\w+)\s+(?:of\s+)?(\d{4})\s+from[^0-9]*([0-9.]+)%"
        match = re.search(cpi_pattern, text, re.IGNORECASE)

        if not match:
            # Fallback pattern
            cpi_pattern2 = r"Inflation Rate in India.*?to\s+([0-9.]+)\s+percent\s+in\s+(\w+)\s+from\s+([0-9.]+)\s+percent"
            match = re.search(cpi_pattern2, text, re.IGNORECASE)
            if match:
                return {
                    "month": match.group(2),
                    "year": "2025",
                    "headline": float(match.group(1)),
                    "previous": float(match.group(3)),
                }

        if not match:
            raise Exception("Failed to extract CPI data from Trading Economics")

        # Extract long-run average
        avg_pattern = r"averaged\s+([0-9.]+)\s+percent"
        avg_match = re.search(avg_pattern, text)

        return {
            "month": match.group(2),
            "year": match.group(3),
            "headline": float(match.group(1)),
            "previous": float(match.group(4)),
            "long_run_avg": float(avg_match.group(1)) if avg_match else 5.71,
        }

    def fetch_wpi_data() -> dict:
        """Fetch WPI from Trading Economics"""
        url = "https://tradingeconomics.com/india/producer-prices-change"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10, verify=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text()

        # Pattern: "dropped 1.21% year-on-year in October 2025, compared with...0.13% rise"
        wpi_pattern = r"(?:dropped|rose|fell|increased)\s+([0-9.]+)%\s+year-on-year\s+in\s+(\w+)\s+(\d{4}).*?(?:from|reversing).*?([0-9.]+)%"
        match = re.search(wpi_pattern, text, re.IGNORECASE)

        if not match:
            # Fallback: Look for WPI Inflation YoY value
            wpi_pattern2 = r"WPI Inflation YoY.*?(-?[0-9.]+).*?(-?[0-9.]+).*?percent"
            match = re.search(wpi_pattern2, text)
            if match:
                return {
                    "month": "October",
                    "year": "2025",
                    "headline": float(match.group(1)),
                    "previous": float(match.group(2)),
                }

        if not match:
            raise Exception("Failed to extract WPI data")

        current = float(match.group(1))
        previous = float(match.group(4))

        # Handle negative values (deflation)
        if "dropped" in text.lower() or "fell" in text.lower():
            current = -current
        if "reversing" in text.lower() and "rise" in text.lower():
            # Previous was positive
            pass
        elif "compared with" in text.lower() and "decline" in text.lower():
            previous = -previous

        return {
            "month": match.group(2),
            "year": match.group(3),
            "headline": current,
            "previous": previous,
        }

    output = [f"INDIA INFLATION REPORT"]

    if indicator.lower() in ["cpi", "both"]:
        try:
            cpi = fetch_cpi_data()
            change = cpi["headline"] - cpi["previous"]

            output.append("CONSUMER PRICE INDEX (CPI) - RETAIL INFLATION")
            output.append(f"Month: {cpi['month']} {cpi['year']}")
            output.append(f"Headline CPI Inflation (YoY): {cpi['headline']:.2f}%")
            output.append(f"Previous Month: {cpi['previous']:.2f}%")
            output.append(f"Change: {change:+.2f} percentage points")

            if "long_run_avg" in cpi:
                output.append(
                    f"Long-run Average (2012-2025): {cpi['long_run_avg']:.2f}%"
                )

            output.append("")

            # Policy interpretation
            if cpi["headline"] > 6.0:
                output.append("Status: ABOVE RBI UPPER TOLERANCE BAND (6%)")
                output.append("Signal: Inflation overheating - Rate hikes likely")
            elif cpi["headline"] > 4.0:
                output.append("Status: WITHIN RBI TOLERANCE BAND (4% ±2%)")
                output.append("Signal: Inflation manageable - Policy neutral")
            elif cpi["headline"] > 2.0:
                output.append("Status: BELOW RBI TARGET (4%)")
                output.append("Signal: Low inflation - Rate cuts possible")
            else:
                output.append("Status: BELOW TOLERANCE BAND (<2%)")
                output.append(
                    "Signal: Very low inflation - Aggressive rate cuts likely"
                )

            output.append("")
        except Exception as e:
            output.append(f"CPI data unavailable: {str(e)}\n")

    if indicator.lower() in ["wpi", "both"]:
        try:
            wpi = fetch_wpi_data()
            change = wpi["headline"] - wpi["previous"]

            output.append("WHOLESALE PRICE INDEX (WPI) - PRODUCER INFLATION")
            output.append(f"Month: {wpi['month']} {wpi['year']}")
            output.append(f"Headline WPI Inflation (YoY): {wpi['headline']:+.2f}%")
            output.append(f"Previous Month: {wpi['previous']:+.2f}%")
            output.append(f"Change: {change:+.2f} percentage points")
            output.append("")

            # Interpretation
            if wpi["headline"] < 0:
                output.append("Status: DEFLATION at wholesale level")
                output.append(
                    "Signal: Producer price pressure easing - Lower input costs"
                )
            elif wpi["headline"] < 2:
                output.append("Status: LOW inflation at wholesale level")
                output.append("Signal: Benign producer prices - Margins improving")
            elif wpi["headline"] < 5:
                output.append("Status: MODERATE inflation at wholesale level")
                output.append("Signal: Steady producer costs - Watch for pass-through")
            else:
                output.append("Status: HIGH inflation at wholesale level")
                output.append("Signal: Rising input costs - Future CPI pressure")

            output.append("")
        except Exception as e:
            output.append(f"WPI data unavailable: {str(e)}\n")

    return "\n".join(output)


def get_india_gdp_data() -> str:
    """
    Fetch India's Gross Domestic Product (GDP) growth rate data.

    GDP measures the total value of all goods and services produced in India.
    Growth rate shows how fast the economy is expanding (or contracting).

    GDP Calculation: GDP = Private Consumption + Government Spending + Investment + Net Exports
    Sectors: Agriculture, Industry (Manufacturing, Mining, Construction), Services

    Use Cases:
    - Primary indicator of economic health
    - GDP >7% = Strong growth economy
    - GDP 5-7% = Moderate growth
    - GDP <5% = Slowdown/concern
    - Quarterly trends show economic momentum
    - Guides RBI policy and market outlook

    Args:
        None

    Returns:
        str: Formatted summary with latest quarterly GDP growth, YoY comparison,
             sectoral breakdown, and economic outlook

    Raises:
        Exception: If data fetching fails
    """

    def fetch_gdp_trading_economics() -> dict:
        url = "https://tradingeconomics.com/india/gdp-growth-annual"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text()

        # Extract pattern like "8.2 percent in the third quarter of 2025"
        current_pattern = (
            r"(\d+\.\d+)\s+percent\s+in\s+the\s+(\w+)\s+quarter\s+of\s+(\d{4})"
        )
        matches = list(re.finditer(current_pattern, text, re.IGNORECASE))

        if not matches:
            raise Exception("Failed to extract GDP data")

        latest = matches[0]

        # Extract average
        avg_pattern = r"averaged\s+(\d+\.\d+)\s+percent"
        avg_match = re.search(avg_pattern, text)

        return {
            "growth_rate": float(latest.group(1)),
            "quarter": latest.group(2),
            "year": latest.group(3),
            "long_run_avg": float(avg_match.group(1)) if avg_match else None,
        }

    try:
        gdp = fetch_gdp_trading_economics()
    except Exception as e:
        return f"GDP data unavailable: {str(e)}"

    output = [
        f"INDIA GDP GROWTH REPORT | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}\n"
    ]

    output.append("GROSS DOMESTIC PRODUCT (GDP) - REAL GROWTH RATE")
    output.append(
        f"Quarter: Q{['first', 'second', 'third', 'fourth'].index(gdp['quarter'].lower()) + 1 if gdp['quarter'].lower() in ['first', 'second', 'third', 'fourth'] else '2'} FY {int(gdp['year']) - 1 if int(gdp['year']) >= 2025 else gdp['year']}-{gdp['year'][2:]}"
    )
    output.append(f"GDP Growth Rate (YoY): {gdp['growth_rate']:.1f}%")
    output.append("")

    if gdp["long_run_avg"]:
        vs_avg = gdp["growth_rate"] - gdp["long_run_avg"]
        output.append(f"Long-run Average: {gdp['long_run_avg']:.1f}%")
        output.append(f"Current vs Average: {vs_avg:+.1f}%")
        output.append("")

    # Economic interpretation
    output.append("Economic Assessment:")
    if gdp["growth_rate"] >= 8.0:
        output.append("STRONG EXPANSION - Robust economic growth")
        output.append("Positive")
    elif gdp["growth_rate"] >= 6.5:
        output.append("HEALTHY GROWTH - Stable economic expansion")
        output.append("Balanced")
    elif gdp["growth_rate"] >= 5.0:
        output.append("MODERATE GROWTH - Below potential expansion")
        output.append("Concerning")
    elif gdp["growth_rate"] >= 3.0:
        output.append("WEAK GROWTH - Economic slowdown")
        output.append("Risky")
    else:
        output.append("SEVERE SLOWDOWN/RECESSION")
        output.append("Crisis")

    return "\n".join(output)


def get_latest_gst_summary() -> str:
    """
    Fetch the latest available gross GST revenue for India and return a
    formatted summary.

    This function:
        - Infers the target month as the previous calendar month relative to today.
        - Constructs the expected GSTN revenue PDF URL for that month using
          the standard naming pattern and parses:
              * Gross GST collections (Rs crore and Rs lakh crore)
              * Year-on-year growth (percent)

    Returns:
        str: Formatted text summary of GST indicators.

    Notes:
        - This is a high-frequency demand snapshot, not a GDP measure.
        - The GST URL pattern is based on current official naming convention and may
          need adjustment if GSTN changes its file naming.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    def _previous_month(today: date) -> tuple[int, int]:
        if today.month == 1:
            return today.year - 1, 12
        return today.year, today.month - 1

    def _fetch_gst_for_month(year: int, month: int):
        """
        Build GSTN monthly revenue PDF URL for the target month and parse:
            - current gross GST (Rs crore)
            - YoY growth (%)

        Pattern:
        'approved_monthly_gst_revenue_data_for_publishing_<mon>_<yyyy>_final.pdf'
        where <mon> is lowercase English month abbreviation (e.g. 'nov'). [web:300]
        """
        month_abbr = date(year, month, 1).strftime("%b").lower()
        fname = (
            f"approved_monthly_gst_revenue_data_for_publishing_"
            f"{month_abbr}_{year}_final.pdf"
        )
        base = "https://tutorial.gst.gov.in/downloads/news/"
        gst_url = base + fname

        try:
            resp = requests.get(gst_url, headers=headers, timeout=20)
        except requests.RequestException:
            return None, None, gst_url
        if resp.status_code != 200:
            return None, None, gst_url

        try:
            with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            return None, None, gst_url

        pat = re.compile(
            r"Total\s+Gross\s+GST\s+Revenue\s+([\d,]+)\s+([\d,]+)\s+"
            r"([+-]?[0-9]+\.[0-9]+|[+-]?\d+)\s*%",
            flags=re.IGNORECASE,
        )
        m = pat.search(text)
        if not m:
            return None, None, gst_url
        try:
            current_crore = float(m.group(2).replace(",", ""))
            yoy = float(m.group(3))
            return current_crore, yoy, gst_url
        except ValueError:
            return None, None, gst_url

    def _fmt(val, suffix: str = "") -> str:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "N/A"
        return f"{val:.2f}{suffix}"

    today = date.today()
    gst_year, gst_month = _previous_month(today)

    gst_crore, gst_yoy, gst_url = _fetch_gst_for_month(gst_year, gst_month)
    if gst_crore is not None:
        gst_lakh_cr = gst_crore / 100000.0
    else:
        gst_lakh_cr = None

    gst_month_name = date(gst_year, gst_month, 1).strftime("%B")
    gst_label = f"{gst_month_name} {gst_year}"

    summary_lines = [
        "India High-Frequency Demand Snapshot (GST)",
        "",
        f"GST (Gross Collections) — {gst_label}:",
        f"- Total gross GST revenue: {_fmt(gst_lakh_cr, ' lakh crore')} "
        f"({_fmt(gst_crore, ' crore')})",
        f"- Year-on-year growth: {_fmt(gst_yoy, ' %')}",
        f"- Source: GSTN monthly revenue PDF: {gst_url}",
    ]

    return "\n".join(summary_lines)


def get_index_valuation_snapshot(
    symbol: str = "NIFTY 50",
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> str:
    """
    Fetch index valuation metrics (P/E, P/B, Dividend Yield) from NSE via
    nsepy.index_pe_pb_div() and provide a percentile-based valuation summary.

    Args:
        symbol: NSE index name as used by NSE, e.g. "NIFTY 50", "NIFTY BANK".
        start:  Start date for history window (default: 2010-01-01).
        end:    End date for history (default: today).

    Returns:
        readable valuation snapshot string.
    """

    if start is None:
        start = date(2010, 1, 1)
    if end is None:
        end = date.today()

    start_str = start.strftime("%d-%b-%Y")
    end_str = end.strftime("%d-%b-%Y")

    try:
        df = index_pe_pb_div(symbol, start_str, end_str)  # [web:404]
    except Exception as e:
        return (
            f"Index Valuation Snapshot – {symbol}\n\n"
            f"Unable to fetch PE/PB/Div history from NSE via nsepy: {e}"
        )

    if df is None or df.empty:
        return (
            f"Index Valuation Snapshot – {symbol}\n\n"
            f"No valuation data returned between {start_str} and {end_str}."
        )

    # Normalise column names (docs: Index Name, pe, pb, divYield, DATE). [web:404]
    df = df.rename(columns=lambda c: c.strip())
    lc_map = {c.lower(): c for c in df.columns}
    try:
        col_pe = lc_map["pe"]
        col_pb = lc_map["pb"]
        col_dy = lc_map["divyield"]
    except KeyError:
        return (
            f"Index Valuation Snapshot – {symbol}\n\n"
            f"Unexpected columns in NSE data: {list(df.columns)}.\n"
            "Expected something like: 'Index Name', 'pe', 'pb', 'divYield', 'DATE'."
        )

    # Clean numeric columns: handle '-', blanks, commas, etc.
    for col in (col_pe, col_pb, col_dy):
        s = df[col].astype(str).str.strip()
        s = s.replace({"-": np.nan, "": np.nan})
        s = s.str.replace(",", "", regex=False)
        df[col] = pd.to_numeric(s, errors="coerce")

    # Keep only rows where all three metrics are present
    valid = df[[col_pe, col_pb, col_dy]].dropna()
    if valid.empty:
        return (
            f"Index Valuation Snapshot – {symbol}\n\n"
            "No rows with all of P/E, P/B and Dividend Yield available "
            "after cleaning (many indices have '-' for some dates)."
        )

    # Use the latest valid row for current values
    latest_idx = valid.index[-1]
    pe_now = float(valid.loc[latest_idx, col_pe])
    pb_now = float(valid.loc[latest_idx, col_pb])
    dy_now = float(valid.loc[latest_idx, col_dy])

    # Figure out the date of that row
    if "DATE" in df.columns:
        latest_date = pd.to_datetime(df.loc[latest_idx, "DATE"]).date()
    else:
        latest_val = latest_idx
        latest_date = latest_val.date() if hasattr(latest_val, "date") else latest_val

    # Historical arrays for percentiles
    pe_hist = valid[col_pe].values
    pb_hist = valid[col_pb].values
    dy_hist = valid[col_dy].values

    def _pct_le(hist: np.ndarray, x: float) -> float:
        return float((hist <= x).mean() * 100.0)

    pe_pct = _pct_le(pe_hist, pe_now)
    pb_pct = _pct_le(pb_hist, pb_now)
    # For dividend yield, higher yield = cheaper - percentile of (>=)
    dy_pct = float((dy_hist >= dy_now).mean() * 100.0)

    def _label_val(pct: float) -> str:
        if pct >= 80:
            return "Expensive (top 20% of history)"
        if pct >= 60:
            return "Slightly expensive"
        if pct <= 20:
            return "Cheap (bottom 20% of history)"
        if pct <= 40:
            return "Slightly cheap"
        return "Fair / middle of range"

    def _label_yield(pct: float) -> str:
        if pct >= 80:
            return "Cheap by yield (top 20% of yield history)"
        if pct >= 60:
            return "Slightly cheap by yield"
        if pct <= 20:
            return "Low yield (expensive by yield)"
        if pct <= 40:
            return "Slightly low yield"
        return "Fair / middle of yield range"

    pe_label = _label_val(pe_pct)
    pb_label = _label_val(pb_pct)
    dy_label = _label_yield(dy_pct)

    return "\n".join(
        [
            f"Index Valuation Snapshot – {symbol}",
            f"As of: {latest_date}",
            f"History window: {start_str} to {end_str} "
            "(NSE index P/E, P/B & Div.Yield data ",
            f"- P/E: {pe_now:.2f}  | Percentile vs history: {pe_pct:.1f}%  - {pe_label}",
            f"- P/B: {pb_now:.2f}  | Percentile vs history: {pb_pct:.1f}%  - {pb_label}",
            f"- Dividend Yield: {dy_now:.2f}%  | Cheapness percentile: {dy_pct:.1f}%  - {dy_label}",
        ]
    )


def get_index_pcr_summary(
    symbol: str = "NIFTY",
    expiry_choice: str = "nearest",
    expiry_index: int | None = None,
) -> str:
    """
    Compute index Put-Call Ratio (OI-based) and a simple risk-sentiment label
    for a chosen expiry, using NSE option-chain data via nsepython. [web:416]

    Args:
        symbol:
            Index symbol as used on NSE option chain, e.g. "NIFTY", "BANKNIFTY".
        expiry_choice:
            One of:
                - "nearest"  : first entry in records['expiryDates'] (default weekly).
                - "second"   : second entry (next weekly), if available.
            Ignored if expiry_index is provided.
        expiry_index:
            Explicit index into records['expiryDates'] (0-based). If not None,
            this overrides expiry_choice.

    Returns:
        Human-readable PCR summary string.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Fetch option chain payload from NSE via nsepython [web:416]
    try:
        chain = option_chain(symbol)
    except Exception as e:
        return (
            f"Index PCR Snapshot - {symbol}\n"
            f"As of: {ts}\n\n"
            f"Unable to fetch option chain from NSE: {e}"
        )

    expiries = chain.get("records", {}).get("expiryDates", [])
    if not expiries:
        return (
            f"Index PCR Snapshot - {symbol}\n"
            f"As of: {ts}\n\n"
            "No expiries found in option-chain payload from NSE."
        )

    # Decide which expiry index to use
    if expiry_index is None:
        if expiry_choice == "nearest":
            idx = 0
        elif expiry_choice == "second":
            idx = 1 if len(expiries) > 1 else 0
        else:
            idx = 0
    else:
        idx = expiry_index

    try:
        expiry = expiries[idx]
    except (IndexError, TypeError):
        return (
            f"Index PCR Snapshot - {symbol}\n"
            f"As of: {ts}\n\n"
            f"Invalid expiry index {idx} for expiry list {expiries}."
        )

    # --- Compute PCR for the chosen expiry (inline helper logic) ---
    ce_oi = 0
    pe_oi = 0

    for rec in chain.get("records", {}).get("data", []):
        if rec.get("expiryDate") != expiry:
            continue
        ce = rec.get("CE")
        pe = rec.get("PE")
        if isinstance(ce, dict):
            ce_oi += ce.get("openInterest", 0) or 0
        if isinstance(pe, dict):
            pe_oi += pe.get("openInterest", 0) or 0

    if ce_oi <= 0:
        return (
            f"Index PCR Snapshot - {symbol}\n"
            f"As of: {ts}\n\n"
            f"Could not compute PCR for expiry index {idx} (expiry={expiry}); "
            f"total Call OI was {ce_oi}."
        )

    pcr = pe_oi / ce_oi

    # Risk-regime mapping
    if pcr < 0.7:
        regime = "Aggressive risk-on (call-heavy, little hedging)"
    elif pcr < 1.0:
        regime = "Risk-on, but not extreme"
    elif pcr < 1.3:
        regime = "Neutral / balanced positioning"
    elif pcr < 1.7:
        regime = "Defensive / hedged (puts building up)"
    else:
        regime = "Extreme fear / heavy hedging (often contrarian bullish)"

    lines = [
        f"Index PCR Snapshot - {symbol}",
        f"As of: {ts}",
        f"Expiry used: {expiry}  (index {idx} in NSE expiry list)",
        f"- Put-Call Ratio (OI-based): {pcr:.2f}",
        f"- Risk regime (for stocks & bonds): {regime}",
        "",
    ]
    return "\n".join(lines)
