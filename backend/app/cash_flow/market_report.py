"""
Market Report Generator
Collects data from all market tools and generates a comprehensive report for bank treasurers.
"""

import os
from datetime import datetime
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Import all market tools
from app.cash_flow.market_tools import (
    get_stock_indices,
    get_forex_performance,
    get_commodity_performance,
    get_bond_yields,
    get_sector_info,
    get_india_vix,
    get_fii_dii_via_nsepython,
    get_advance_decline_analysis,
    get_india_pmi_data,
    get_india_inflation_data,
    get_india_gdp_data,
    get_latest_gst_summary,
    get_index_valuation_snapshot,
    get_index_pcr_summary,
    all_sector_data
)

load_dotenv()

# Initialize OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


def collect_all_market_data() -> Dict[str, Any]:
    """
    Calls all market tools and collects comprehensive market data.
    
    Returns:
        Dict containing all market data from various tools
    """
    market_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "errors": []
    }
    
    # 1. Stock Indices (NIFTY50, SENSEX30, BANKNIFTY)
    print("📊 Fetching stock indices...")
    try:
        market_data["stock_indices"] = {
            "nifty50": get_stock_indices("NIFTY50"),
            "sensex30": get_stock_indices("SENSEX30"),
            "banknifty": get_stock_indices("BANKNIFTY")
        }
    except Exception as e:
        market_data["errors"].append(f"Stock Indices: {str(e)}")
        market_data["stock_indices"] = None

    # 2. Forex Performance (USD/INR)
    print("💱 Fetching forex data...")
    try:
        market_data["forex"] = {
            "usd_inr": get_forex_performance("USD", "INR", period="1mo", interval="1d"),
            "eur_inr": get_forex_performance("EUR", "INR", period="1mo", interval="1d"),
            "gbp_inr": get_forex_performance("GBP", "INR", period="1mo", interval="1d")
        }
    except Exception as e:
        market_data["errors"].append(f"Forex: {str(e)}")
        market_data["forex"] = None

    # 3. Commodities (Gold, Crude Oil, Silver)
    print("🛢️ Fetching commodity data...")
    try:
        market_data["commodities"] = {
            "gold": get_commodity_performance("gold"),
            "silver": get_commodity_performance("silver"),
            "crude_oil_brent": get_commodity_performance("brent")
        }
    except Exception as e:
        market_data["errors"].append(f"Commodities: {str(e)}")
        market_data["commodities"] = None

    # 4. Bond Yields
    print("📈 Fetching bond yields...")
    try:
        market_data["bond_yields"] = get_bond_yields()
    except Exception as e:
        market_data["errors"].append(f"Bond Yields: {str(e)}")
        market_data["bond_yields"] = None

    # 5. Key Sector Info (Banking, IT, Finance)
    print("🏭 Fetching sector data...")
    try:
        market_data["sectors"] = {
            "banking": get_sector_info("BANK"),
            "it": get_sector_info("IT"),
            "finance": get_sector_info("FINANCE"),
            "pharma": get_sector_info("PHARMA"),
            "auto": get_sector_info("AUTO")
        }
    except Exception as e:
        market_data["errors"].append(f"Sectors: {str(e)}")
        market_data["sectors"] = None

    # 6. India VIX (Volatility Index)
    print("📉 Fetching India VIX...")
    try:
        market_data["india_vix"] = get_india_vix(period="1mo")
    except Exception as e:
        market_data["errors"].append(f"India VIX: {str(e)}")
        market_data["india_vix"] = None

    # 7. FII/DII Data
    print("🏦 Fetching FII/DII data...")
    try:
        market_data["fii_dii"] = get_fii_dii_via_nsepython()
    except Exception as e:
        market_data["errors"].append(f"FII/DII: {str(e)}")
        market_data["fii_dii"] = None

    # 8. Advance/Decline Analysis
    print("📊 Fetching advance/decline data...")
    try:
        market_data["advance_decline"] = {
            "overall": get_advance_decline_analysis("all"),
            "nifty50": get_advance_decline_analysis("nifty50"),
            "banknifty": get_advance_decline_analysis("banknifty")
        }
    except Exception as e:
        market_data["errors"].append(f"Advance/Decline: {str(e)}")
        market_data["advance_decline"] = None

    # 9. PMI Data
    print("📋 Fetching PMI data...")
    try:
        market_data["pmi"] = get_india_pmi_data(sector="both")
    except Exception as e:
        market_data["errors"].append(f"PMI: {str(e)}")
        market_data["pmi"] = None

    # 10. Inflation Data (CPI & WPI)
    print("💹 Fetching inflation data...")
    try:
        market_data["inflation"] = get_india_inflation_data(indicator="both")
    except Exception as e:
        market_data["errors"].append(f"Inflation: {str(e)}")
        market_data["inflation"] = None

    # 11. GDP Data
    print("📈 Fetching GDP data...")
    try:
        market_data["gdp"] = get_india_gdp_data()
    except Exception as e:
        market_data["errors"].append(f"GDP: {str(e)}")
        market_data["gdp"] = None

    # 12. GST Collections
    print("🧾 Fetching GST data...")
    try:
        market_data["gst"] = get_latest_gst_summary()
    except Exception as e:
        market_data["errors"].append(f"GST: {str(e)}")
        market_data["gst"] = None

    # 13. Index Valuation (P/E, P/B)
    print("📊 Fetching valuation metrics...")
    try:
        market_data["valuation"] = {
            "nifty50": get_index_valuation_snapshot("NIFTY 50"),
            "nifty_bank": get_index_valuation_snapshot("NIFTY BANK")
        }
    except Exception as e:
        market_data["errors"].append(f"Valuation: {str(e)}")
        market_data["valuation"] = None

    # 14. Put-Call Ratio
    print("📉 Fetching PCR data...")
    try:
        market_data["pcr"] = {
            "nifty": get_index_pcr_summary("NIFTY", expiry_choice="nearest"),
            "banknifty": get_index_pcr_summary("BANKNIFTY", expiry_choice="nearest")
        }
    except Exception as e:
        market_data["errors"].append(f"PCR: {str(e)}")
        market_data["pcr"] = None

    print("✅ Data collection complete!")
    return market_data


def generate_market_report(market_data: Dict[str, Any]) -> str:
    """
    Uses OpenAI API to generate a formatted market report for bank treasurers.
    Output is in Markdown format suitable for PDF conversion.
    
    Args:
        market_data: Dictionary containing all collected market data
        
    Returns:
        Formatted market report string in Markdown format
    """
    if not OPENAI_API_KEY:
        return "❌ OPENAI_API_KEY not found. Please set it in your .env file."
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    report_date = market_data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"))
    
    system_prompt = """You are an expert financial analyst preparing a daily market intelligence report for a Bank Treasurer in India.

**IMPORTANT: Output the report in proper Markdown format suitable for PDF conversion.**

Your report should be:
1. **Executive Summary Ready** - Start with key takeaways a busy treasurer can read in 30 seconds
2. **Action-Oriented** - Highlight what requires attention or decision-making
3. **Risk-Focused** - Emphasize liquidity risk, interest rate risk, forex risk, and market volatility
4. **Treasury-Relevant** - Focus on:
   - Bond yields and interest rate movements (affects ALM)
   - Forex trends (affects trade finance & hedging)
   - Liquidity conditions (FII/DII flows, market breadth)
   - Inflation & RBI policy implications
   - Market volatility (VIX) for risk management

**FORMAT REQUIREMENTS (Markdown for PDF):**

Use this exact structure with proper Markdown syntax:

```
# Daily Treasury Market Report

**Report Date:** [DATE]  
**Prepared For:** Bank Treasury Department  
**Classification:** Internal Use Only

---

## Executive Summary

> **Key Highlights:**
> - Point 1
> - Point 2
> - Point 3

| Metric | Value | Change | Signal |
|--------|-------|--------|--------|
| NIFTY 50 | xxx | +x.x% | Bullish/Bearish |
| India VIX | xx.x | +x.x% | Low/High Vol |
| 10Y G-Sec | x.xx% | +xbps | Rising/Falling |
| USD/INR | xx.xx | +x.x% | Appreciating/Depreciating |

---

## 1. Market Snapshot

### 1.1 Equity Indices
[Use tables for data]

### 1.2 Sectoral Performance
[Use tables]

---

## 2. Interest Rate & Bond Market

### 2.1 Government Bond Yields
[Table with yields]

### 2.2 Rate Outlook
[Analysis text]

---

## 3. Forex Market

### 3.1 Currency Performance
[Table with forex data]

### 3.2 Hedging Implications
[Analysis]

---

## 4. Liquidity Conditions

### 4.1 FII/DII Flows
[Table]

### 4.2 Market Breadth
[Advance/Decline data]

### 4.3 Options Sentiment (PCR)
[PCR analysis]

---

## 5. Economic Indicators

### 5.1 GDP & Growth
[Data]

### 5.2 Inflation (CPI/WPI)
[Data]

### 5.3 PMI Data
[Manufacturing & Services]

### 5.4 GST Collections
[Data]

---

## 6. Valuation Metrics

[P/E, P/B percentile analysis]

---

## 7. Risk Assessment

### Key Risks to Monitor:
1. **Risk 1:** Description
2. **Risk 2:** Description
3. **Risk 3:** Description

### Risk Matrix:
| Risk Category | Level | Trend |
|--------------|-------|-------|
| Interest Rate Risk | High/Medium/Low | ↑/↓/→ |
| Forex Risk | High/Medium/Low | ↑/↓/→ |
| Liquidity Risk | High/Medium/Low | ↑/↓/→ |
| Market Risk | High/Medium/Low | ↑/↓/→ |

---

## 8. Treasury Action Items

### Immediate Actions (Today):
- [ ] Action item 1
- [ ] Action item 2

### This Week:
- [ ] Action item 1
- [ ] Action item 2

### Strategic Recommendations:
1. **Cash Management:** Recommendation
2. **Bond Portfolio:** Recommendation
3. **Forex Hedging:** Recommendation
4. **Liquidity Buffer:** Recommendation

---

## Appendix: Data Sources

- NSE India
- RBI
- Trading Economics
- Yahoo Finance

---

*This report is generated automatically and should be validated before making investment decisions.*
```

**RULES:**
1. Use proper Markdown headers (# ## ###)
2. Use tables (| col1 | col2 |) for numerical data
3. Use blockquotes (>) for important highlights
4. Use bullet points (-) and numbered lists (1.)
5. Use horizontal rules (---) to separate sections
6. Use **bold** for emphasis on important numbers
7. Use checkboxes (- [ ]) for action items
8. Include proper spacing between sections
9. Keep tables aligned and readable
10. Use emojis sparingly (only in headers if at all for PDF)"""

    user_prompt = f"""Based on the following market data collected at {report_date}, 
generate a comprehensive daily market report for a Bank Treasurer in India.

**OUTPUT FORMAT: Markdown (README style) suitable for PDF conversion**

=== RAW MARKET DATA ===

{format_market_data_for_prompt(market_data)}

=== END OF DATA ===

Please analyze this data and generate a professional treasury market report in proper Markdown format.
- Use tables for all numerical data
- Use proper headers and sections
- Include a risk matrix
- Provide specific, actionable recommendations
- If any data is missing or shows errors, note it but continue with available data.
- Focus on actionable insights relevant to bank treasury operations in India."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=6000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error generating report: {str(e)}"


def format_market_data_for_prompt(market_data: Dict[str, Any]) -> str:
    """Format market data into a readable string for the LLM prompt."""
    sections = []
    
    # Stock Indices
    if market_data.get("stock_indices"):
        sections.append("=== STOCK INDICES ===")
        for name, data in market_data["stock_indices"].items():
            if isinstance(data, dict):
                sections.append(f"\n{name.upper()}:")
                sections.append(f"  Current Price: {data.get('regularMarketPrice', 'N/A')}")
                sections.append(f"  Day Change: {data.get('regularMarketChange', 'N/A')} ({data.get('regularMarketChangePercent', 'N/A')}%)")
                sections.append(f"  Day High: {data.get('regularMarketDayHigh', 'N/A')}")
                sections.append(f"  Day Low: {data.get('regularMarketDayLow', 'N/A')}")
                sections.append(f"  52W High: {data.get('fiftyTwoWeekHigh', 'N/A')}")
                sections.append(f"  52W Low: {data.get('fiftyTwoWeekLow', 'N/A')}")
    
    # Forex
    if market_data.get("forex"):
        sections.append("\n=== FOREX ===")
        for pair, data in market_data["forex"].items():
            sections.append(f"\n{pair.upper()}:")
            sections.append(str(data))
    
    # Commodities
    if market_data.get("commodities"):
        sections.append("\n=== COMMODITIES ===")
        for name, data in market_data["commodities"].items():
            sections.append(f"\n{name.upper()}:")
            sections.append(str(data))
    
    # Bond Yields
    if market_data.get("bond_yields"):
        sections.append("\n=== INDIAN GOVERNMENT BOND YIELDS ===")
        for bond in market_data["bond_yields"]:
            sections.append(f"  {bond.get('Bonds', 'N/A')}: Yield={bond.get('Yield', 'N/A')}%, Day={bond.get('Day', 'N/A')}%, Month={bond.get('Month', 'N/A')}%")
    
    # India VIX
    if market_data.get("india_vix"):
        sections.append("\n=== INDIA VIX (VOLATILITY) ===")
        vix = market_data["india_vix"]
        sections.append(f"  Current VIX: {vix.get('current_vix', 'N/A')}")
        sections.append(f"  Day Change: {vix.get('day_change', 'N/A')} ({vix.get('day_change_pct', 'N/A')}%)")
        sections.append(f"  Regime: {vix.get('volatility_regime', 'N/A')}")
        sections.append(f"  Signal: {vix.get('market_signal', 'N/A')}")
    
    # FII/DII
    if market_data.get("fii_dii"):
        sections.append("\n=== FII/DII FLOWS ===")
        sections.append(str(market_data["fii_dii"]))
    
    # Advance/Decline
    if market_data.get("advance_decline"):
        sections.append("\n=== MARKET BREADTH (ADVANCE/DECLINE) ===")
        for category, data in market_data["advance_decline"].items():
            if isinstance(data, dict) and "error" not in data:
                sections.append(f"\n{category.upper()}:")
                sections.append(f"  Advances: {data.get('advances', 'N/A')} | Declines: {data.get('declines', 'N/A')}")
                sections.append(f"  A/D Ratio: {data.get('ad_ratio', 'N/A')}")
                sections.append(f"  Near 52W High: {data.get('near_52w_high', 'N/A')} | Near 52W Low: {data.get('near_52w_low', 'N/A')}")
    
    # Sectors
    if market_data.get("sectors"):
        sections.append("\n=== KEY SECTORS ===")
        for sector, data in market_data["sectors"].items():
            if isinstance(data, dict) and "error" not in data:
                sections.append(f"  {sector.upper()}: {data.get('lastPrice', 'N/A')} ({data.get('pChange', 'N/A')}%)")
    
    # PMI
    if market_data.get("pmi"):
        sections.append("\n=== PMI DATA ===")
        sections.append(str(market_data["pmi"]))
    
    # Inflation
    if market_data.get("inflation"):
        sections.append("\n=== INFLATION DATA ===")
        sections.append(str(market_data["inflation"]))
    
    # GDP
    if market_data.get("gdp"):
        sections.append("\n=== GDP DATA ===")
        sections.append(str(market_data["gdp"]))
    
    # GST
    if market_data.get("gst"):
        sections.append("\n=== GST COLLECTIONS ===")
        sections.append(str(market_data["gst"]))
    
    # Valuation
    if market_data.get("valuation"):
        sections.append("\n=== INDEX VALUATION (P/E, P/B) ===")
        for index, data in market_data["valuation"].items():
            sections.append(f"\n{index.upper()}:")
            sections.append(str(data))
    
    # PCR
    if market_data.get("pcr"):
        sections.append("\n=== PUT-CALL RATIO ===")
        for index, data in market_data["pcr"].items():
            sections.append(f"\n{index.upper()}:")
            sections.append(str(data))
    
    # Errors
    if market_data.get("errors"):
        sections.append("\n=== DATA COLLECTION ERRORS ===")
        for error in market_data["errors"]:
            sections.append(f"  ⚠️ {error}")
    
    return "\n".join(sections)


def save_report_to_markdown(report: str, filename: str = None) -> str:
    """
    Save the markdown report to a file for PDF conversion.
    
    Args:
        report: The markdown formatted report string
        filename: Optional filename (defaults to timestamped name)
        
    Returns:
        Path to the saved file
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"market_report_{timestamp}.md"
    
    # Ensure reports directory exists
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"📄 Report saved to: {filepath}")
    return filepath


def get_full_market_report(save_markdown: bool = True) -> Dict[str, Any]:
    """
    Main function to generate complete market report.
    
    Args:
        save_markdown: If True, saves the report as a .md file for PDF conversion
    
    Returns:
        Dictionary with raw_data, report, markdown_path, and metadata
    """
    print("\n" + "="*60)
    print("🏦 BANK TREASURER MARKET REPORT GENERATOR")
    print("="*60 + "\n")
    
    # Collect all market data
    print("📡 Collecting market data from all sources...\n")
    market_data = collect_all_market_data()
    
    # Generate AI report
    print("\n🤖 Generating AI-powered report in Markdown format...\n")
    report = generate_market_report(market_data)
    
    result = {
        "timestamp": market_data.get("timestamp"),
        "raw_data": market_data,
        "report": report,
        "errors": market_data.get("errors", []),
        "markdown_path": None
    }
    
    # Save to markdown file if requested
    if save_markdown:
        try:
            result["markdown_path"] = save_report_to_markdown(report)
            print(f"\n✅ Markdown report saved! Convert to PDF using:")
            print(f"   - VS Code: Open .md file → Ctrl+Shift+P → 'Markdown: Export to PDF'")
            print(f"   - Pandoc: pandoc {result['markdown_path']} -o report.pdf")
            print(f"   - Online: Upload to https://md2pdf.netlify.app/")
        except Exception as e:
            print(f"⚠️ Could not save markdown file: {e}")
    
    return result


# For direct execution / testing
if __name__ == "__main__":
    result = get_full_market_report(save_markdown=True)
    print("\n" + "="*60)
    print("📋 GENERATED REPORT (Markdown Format)")
    print("="*60 + "\n")
    print(result["report"])
    
    if result.get("markdown_path"):
        print("\n" + "="*60)
        print(f"📁 Report saved to: {result['markdown_path']}")
        print("="*60)