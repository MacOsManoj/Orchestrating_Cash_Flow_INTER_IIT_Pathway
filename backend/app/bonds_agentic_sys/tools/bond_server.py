"""
Bond Forecasting Server - STATIC MODE with Daily Updates
MCP server with automatic daily recomputation
"""

import pathway as pw
import json
import threading
import time
import os
import pandas as pd
from datetime import datetime, timedelta

# Import core forecasting logic
from bond_forecast_core import (
    COMPUTED_DATA,
    get_bond_by_identifier,
    get_all_bond_symbols,
    price_bond_dirty_price,
    calculate_bond_ytm_today,
    calculate_bond_duration_and_convexity,
    filter_bonds_by_criteria,
    get_yield_curve_for_date,
    recommend_bonds_by_criteria,
    INPUT_FILES,
    OUTPUT_DIR,
    FORECAST_DAYS,
    LOOKBACK_DAYS,
    get_maturity,
    get_forecast_day,
    get_predicted_close,
    get_predicted_return,
)

# ==================== SERVER CONFIGURATION ====================

MCP_HOST = "localhost"
MCP_PORT = 8123

# ==================== PATHWAY MCP SCHEMAS ====================


class EmptySchema(pw.Schema):
    pass


class YieldRequestSchema(pw.Schema):
    maturity: int


class ForecastRequestSchema(pw.Schema):
    maturity: int
    days_ahead: int


class BondIdentifierRequestSchema(pw.Schema):
    bond_identifier: str
    days_ahead: int


class SearchBondsSchema(pw.Schema):
    search_term: str


class FilterBondsSchema(pw.Schema):
    min_coupon: float
    max_coupon: float
    min_years_to_maturity: float
    max_years_to_maturity: float
    symbol_contains: str
    name_contains: str


class BondYTMSchema(pw.Schema):
    bond_identifier: str


class BondDurationSchema(pw.Schema):
    bond_identifier: str


class CompareBondsSchema(pw.Schema):
    bond_identifiers: str
    days_ahead: int


class YieldCurveDateSchema(pw.Schema):
    days_ahead: int


class RecommendBondsSchema(pw.Schema):
    target_yield: float
    max_risk: str
    investment_horizon: float
    sort_by: str


# ==================== DATA COMPUTATION ====================


def compute_all_data():
    yield_forecast_file = "output_forecasts/final_forecasts.csv"
    try:
        print("  Reading forecast CSV...")
        forecast_df = pd.read_csv(yield_forecast_file)

        if forecast_df.empty:
            print(" Forecast CSV is empty")
            return False

        print(f"  Found {len(forecast_df)} rows in output")
        print("  Filtering for latest forecast generation date...")

        # Filter for latest forecast generation date
        forecast_df["Forecast_Generation_Date"] = pd.to_datetime(
            forecast_df["Forecast_Generation_Date"]
        )
        latest_date = forecast_df["Forecast_Generation_Date"].max()
        forecast_df = forecast_df[
            forecast_df["Forecast_Generation_Date"] == latest_date
        ].copy()
        forecast_df["Target_Date"] = pd.to_datetime(
            forecast_df["Target_Date"]
        ).dt.strftime("%Y-%m-%d")

        COMPUTED_DATA["forecast_df"] = forecast_df

        #  NEW: Extract latest ACTUAL yields from raw CSV files (not predictions!)
        latest_yields = {}
        try:
            print("   Reading latest actual yields from CSV files...")

            # Read each maturity's CSV and get the latest Close value
            for maturity, csv_path in INPUT_FILES.items():
                try:
                    # Read the CSV
                    df = pd.read_csv(csv_path)

                    if df.empty:
                        print(f"       {maturity}Y CSV is empty")
                        continue

                    # Get the latest (most recent) Close value
                    df["Date"] = pd.to_datetime(df["Date"])
                    df = df.sort_values("Date", ascending=False)
                    latest_close_raw = df.iloc[0]["Close"]
                    latest_date = df.iloc[0]["Date"]

                    #  Handle percentage strings like "5.704%"
                    if isinstance(latest_close_raw, str):
                        latest_close_raw = latest_close_raw.strip().replace("%", "")
                    latest_close = float(latest_close_raw)

                    #  Store as-is (already in percentage form like 5.704)
                    latest_yields[float(maturity)] = latest_close

                    print(
                        f"      {maturity}Y: {latest_close}% (from {latest_date.strftime('%Y-%m-%d')})"
                    )

                except Exception as e:
                    print(f"       Could not read {maturity}Y: {e}")
                    continue

            print(
                f"   Extracted latest ACTUAL yields for {len(latest_yields)} maturities"
            )

        except Exception as e:
            print(f"    Could not extract latest yields: {e}")
            latest_yields = {}

        COMPUTED_DATA["latest_yields"] = latest_yields

        # Ensure bonds are loaded (they're loaded at module import, but verify)
        if not COMPUTED_DATA.get("bonds_list"):
            print("  Loading bonds from CSV...")
            from bond_forecast_core import load_bonds_from_csv, BONDS_CSV_FILE

            bonds_list, skipped_bonds = load_bonds_from_csv(BONDS_CSV_FILE)
            COMPUTED_DATA["bonds_list"] = bonds_list
            COMPUTED_DATA["skipped_bonds"] = skipped_bonds
            print(f"  Loaded {len(bonds_list)} bonds")
        else:
            print(f"  Bonds already loaded: {len(COMPUTED_DATA['bonds_list'])} bonds")

        COMPUTED_DATA["ready"] = True
        COMPUTED_DATA["last_update"] = datetime.now()

        return True

    except Exception as e:
        print(f" Error loading forecasts: {e}")
        import traceback

        traceback.print_exc()
        return False


# ==================== MCP TOOLS ====================

from pathway.xpacks.llm.mcp_server import McpServable, McpServer, PathwayMcp


class LatestYieldsTool(McpServable):
    """Get latest yields for all maturities"""

    def handler(self, input_table):
        if not COMPUTED_DATA["ready"]:
            result = json.dumps({"status": "Data still loading..."})
        else:
            yields_dict = {
                f"{k}Y": v for k, v in sorted(COMPUTED_DATA["latest_yields"].items())
            }
            last_update = COMPUTED_DATA.get("last_update")
            result = json.dumps(
                {
                    "yields": yields_dict,
                    "last_update": str(last_update) if last_update else "N/A",
                },
                indent=2,
            )
        return input_table.select(result=result)

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_latest_yields", request_handler=self.handler, schema=EmptySchema
        )


class YieldForecastTool(McpServable):
    """Get yield forecast for specific maturity"""

    def handler(self, input_table):
        def get_forecast(maturity, days_ahead):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})
            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                return json.dumps({"error": "No forecast data available"})
            mat_data = forecast_df[forecast_df["Maturity"] == maturity]
            if mat_data.empty:
                return json.dumps({"error": f"No forecast for {maturity}Y maturity"})
            filtered = (
                mat_data[mat_data["Prediction_Day"] <= days_ahead]
                if days_ahead > 0
                else mat_data
            )
            if filtered.empty:
                return json.dumps({"error": "No data for specified days"})
            results = []
            for _, row in filtered.iterrows():
                results.append(
                    {
                        "day": int(row["Prediction_Day"]),
                        "date": row["Target_Date"],
                        "predicted_yield": round(float(row["Predicted_Yield"]), 3),
                        "predicted_return": round(float(row["Predicted_Return"]), 4),
                    }
                )
            return json.dumps(
                {"maturity": f"{maturity}Y", "forecasts": results}, indent=2
            )

        return input_table.select(
            result=pw.apply(get_forecast, pw.this.maturity, pw.this.days_ahead)
        )

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_yield_forecast",
            request_handler=self.handler,
            schema=ForecastRequestSchema,
        )


class AllForecastsTool(McpServable):
    """Get all yield forecasts"""

    def handler(self, input_table):
        if not COMPUTED_DATA["ready"]:
            result = json.dumps({"status": "Data still loading..."})
        else:
            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                result = json.dumps({"error": "No forecast data available"})
            else:
                all_forecasts = []
                for mat in sorted(forecast_df["Maturity"].unique()):
                    mat_data = forecast_df[forecast_df["Maturity"] == mat]
                    forecasts = []
                    for _, row in mat_data.iterrows():
                        forecasts.append(
                            {
                                "day": int(row["Prediction_Day"]),
                                "date": row["Target_Date"],
                                "predicted_yield": round(
                                    float(row["Predicted_Yield"]), 3
                                ),
                            }
                        )
                    all_forecasts.append(
                        {"maturity": f"{mat}Y", "forecasts": forecasts}
                    )
                result = json.dumps(all_forecasts, indent=2)

        return input_table.select(result=result)

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_all_yield_forecasts", request_handler=self.handler, schema=EmptySchema
        )


class BondPriceBySymbolTool(McpServable):
    """Get bond price by symbol/ISIN"""

    def handler(self, input_table):
        def get_price(bond_identifier, days_ahead):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bond = get_bond_by_identifier(bond_identifier)

            if not bond:
                skipped = COMPUTED_DATA.get("skipped_bonds", [])
                for skip in skipped:
                    if (
                        skip["symbol"].upper() == bond_identifier.upper()
                        or skip["isin"].upper() == bond_identifier.upper()
                    ):
                        return json.dumps(
                            {
                                "error": f"Bond '{bond_identifier}' cannot be priced",
                                "reason": skip["reason"],
                            }
                        )
                available_bonds = get_all_bond_symbols()
                return json.dumps(
                    {
                        "error": f"Bond '{bond_identifier}' not found",
                        "available_count": len(available_bonds),
                        "hint": "Use search_bonds to find valid identifiers",
                    }
                )

            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                return json.dumps({"error": "No yield forecasts available"})

            unique_dates = sorted(forecast_df["Target_Date"].unique())

            if days_ahead > 0:
                if days_ahead <= len(unique_dates):
                    dates_to_price = [unique_dates[days_ahead - 1]]
                else:
                    return json.dumps(
                        {"error": f"Only {len(unique_dates)} days available"}
                    )
            else:
                dates_to_price = unique_dates

            results = []
            for date_str in dates_to_price:
                day_data = forecast_df[forecast_df["Target_Date"] == date_str]
                if day_data.empty:
                    continue

                curve_today = {}
                for _, row in day_data.iterrows():
                    curve_today[float(row["Maturity"])] = (
                        float(row["Predicted_Yield"]) / 100.0
                    )

                price = price_bond_dirty_price(bond, curve_today, date_str)

                if price is not None:
                    ytm = calculate_bond_ytm_today(bond, curve_today, date_str)
                    results.append(
                        {
                            "date": date_str,
                            "predicted_price": round(price, 2),
                            "ytm": round(ytm * 100, 3) if ytm else None,
                        }
                    )

            if not results:
                return json.dumps({"error": "Pricing calculation failed"})

            if days_ahead > 0:
                res = results[0]
                return json.dumps(
                    {
                        "bond_symbol": bond["symbol"],
                        "bond_isin": bond["isin"],
                        "bond_name": bond["name"],
                        "day": days_ahead,
                        "date": res["date"],
                        "estimated_price": res["predicted_price"],
                        "ytm_percent": res["ytm"],
                        "maturity_date": bond["maturity_date"],
                        "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                        "bond_type": bond.get("bond_type", "Corporate"),  #  NEW!
                        "rating": bond.get("rating", "A"),  #  NEW!
                        "risk_level": bond.get("risk_level", "Medium"),  #  NEW!
                    },
                    indent=2,
                )
            else:
                #  Add safety check
                if len(results) == 0:
                    return json.dumps({"error": "No forecast data available"})

                first_price = results[0]["predicted_price"]
                last_price = results[-1]["predicted_price"]
                price_change = last_price - first_price
                pct_change = (
                    (price_change / first_price) * 100 if first_price != 0 else 0
                )

                #  Get LTP from bond data
                ltp = bond.get("last_traded_price")

                return json.dumps(
                    {
                        "bond_symbol": bond["symbol"],
                        "bond_isin": bond["isin"],
                        "bond_name": bond["name"],
                        "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                        "maturity_date": bond["maturity_date"],
                        "bond_type": bond.get("bond_type", "Corporate"),  #  NEW!
                        "rating": bond.get("rating", "A"),  #  NEW!
                        "risk_level": bond.get("risk_level", "Medium"),  #  NEW!
                        "last_traded_price": round(ltp, 2) if ltp else None,  #  NEW!
                        "starting_price": round(first_price, 2),
                        "ending_price": round(last_price, 2),
                        "price_change": round(price_change, 2),
                        "pct_change": round(pct_change, 2),
                        "forecasts": [
                            {
                                "date": r["date"],
                                "price": r["predicted_price"],
                                "ytm_percent": r["ytm"],  #  NEW!
                            }
                            for r in results
                        ],
                    },
                    indent=2,
                )

        return input_table.select(
            result=pw.apply(get_price, pw.this.bond_identifier, pw.this.days_ahead)
        )

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_bond_price",
            request_handler=self.handler,
            schema=BondIdentifierRequestSchema,
        )


class ListBondsTool(McpServable):
    """List all available bonds"""

    def handler(self, input_table):
        if not COMPUTED_DATA["ready"]:
            result = json.dumps({"status": "Data still loading..."})
        else:
            bonds_list = COMPUTED_DATA.get("bonds_list", [])
            bonds_info = [
                {
                    "symbol": b["symbol"],
                    "isin": b["isin"],
                    "name": b["name"],
                    "coupon_rate": round(b["coupon_rate"] * 100, 2),
                    "maturity_date": b["maturity_date"],
                    "bond_type": b.get("bond_type", "Corporate"),  #  NEW!
                    "rating": b.get("rating", "A"),  #  NEW!
                    "risk_level": b.get("risk_level", "Medium"),  #  NEW!
                    "last_traded_price": b.get("last_traded_price"),  #  NEW!
                }
                for b in bonds_list
            ]
            result = json.dumps(
                {"total_bonds": len(bonds_info), "bonds": bonds_info}, indent=2
            )
        return input_table.select(result=result)

    def register_mcp(self, server: McpServer):
        server.tool("list_bonds", request_handler=self.handler, schema=EmptySchema)


class SearchBondsTool(McpServable):
    """Search for bonds"""

    def handler(self, input_table):
        def search(search_term):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            search_term = search_term.strip().upper()
            bonds_list = COMPUTED_DATA.get("bonds_list", [])

            matches = []
            for bond in bonds_list:
                if (
                    search_term in bond["symbol"].upper()
                    or search_term in bond["isin"].upper()
                    or search_term in bond["description"].upper()
                ):
                    matches.append(
                        {
                            "symbol": bond["symbol"],
                            "isin": bond["isin"],
                            "name": bond["name"],
                            "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                            "maturity_date": bond["maturity_date"],
                        }
                    )

            return json.dumps(
                {"search_term": search_term, "matches": len(matches), "bonds": matches},
                indent=2,
            )

        return input_table.select(result=pw.apply(search, pw.this.search_term))

    def register_mcp(self, server: McpServer):
        server.tool(
            "search_bonds", request_handler=self.handler, schema=SearchBondsSchema
        )


class BondInfoTool(McpServable):
    """Get bond information"""

    def handler(self, input_table):
        def get_info(bond_identifier):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bond = get_bond_by_identifier(bond_identifier)
            if not bond:
                return json.dumps({"error": f"Bond '{bond_identifier}' not found"})

            maturity_date = datetime.strptime(bond["maturity_date"], "%Y-%m-%d")
            years_to_maturity = (maturity_date - datetime.now()).days / 365.25

            return json.dumps(
                {
                    "symbol": bond["symbol"],
                    "isin": bond["isin"],
                    "name": bond["name"],
                    "face_value": bond["face_value"],
                    "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                    "coupon_frequency": bond["coupon_frequency"],
                    "maturity_date": bond["maturity_date"],
                    "years_to_maturity": round(years_to_maturity, 2),
                    "description": bond["description"],
                },
                indent=2,
            )

        return input_table.select(result=pw.apply(get_info, pw.this.bond_identifier))

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_bond_info",
            request_handler=self.handler,
            schema=BondIdentifierRequestSchema,
        )


class CalculateBondYTMTool(McpServable):
    """Calculate bond YTM"""

    def handler(self, input_table):
        def calc_ytm(bond_identifier):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bond = get_bond_by_identifier(bond_identifier)
            if not bond:
                return json.dumps({"error": f"Bond '{bond_identifier}' not found"})

            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                return json.dumps({"error": "No yield data available"})

            today = sorted(forecast_df["Target_Date"].unique())[0]
            day_data = forecast_df[forecast_df["Target_Date"] == today]

            curve_data = {}
            for _, row in day_data.iterrows():
                curve_data[float(row["Maturity"])] = (
                    float(row["Predicted_Yield"]) / 100.0
                )

            ytm = calculate_bond_ytm_today(bond, curve_data, today)

            if ytm is None:
                return json.dumps({"error": "Could not calculate YTM"})

            return json.dumps(
                {
                    "bond_symbol": bond["symbol"],
                    "bond_name": bond["name"],
                    "ytm_percent": round(ytm * 100, 3),
                    "valuation_date": today,
                },
                indent=2,
            )

        return input_table.select(result=pw.apply(calc_ytm, pw.this.bond_identifier))

    def register_mcp(self, server: McpServer):
        server.tool(
            "calculate_bond_ytm", request_handler=self.handler, schema=BondYTMSchema
        )


class CalculateBondDurationTool(McpServable):
    """Calculate bond duration and convexity"""

    def handler(self, input_table):
        def calc_duration(bond_identifier):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bond = get_bond_by_identifier(bond_identifier)
            if not bond:
                return json.dumps({"error": f"Bond '{bond_identifier}' not found"})

            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                return json.dumps({"error": "No yield data available"})

            today = sorted(forecast_df["Target_Date"].unique())[0]
            day_data = forecast_df[forecast_df["Target_Date"] == today]

            curve_data = {}
            for _, row in day_data.iterrows():
                curve_data[float(row["Maturity"])] = (
                    float(row["Predicted_Yield"]) / 100.0
                )

            ytm = calculate_bond_ytm_today(bond, curve_data, today)
            if ytm is None:
                return json.dumps({"error": "Could not calculate YTM"})

            duration_data = calculate_bond_duration_and_convexity(bond, ytm, today)
            if duration_data is None:
                return json.dumps({"error": "Could not calculate duration"})

            return json.dumps(
                {
                    "bond_symbol": bond["symbol"],
                    "bond_name": bond["name"],
                    "macaulay_duration": round(duration_data["macaulay_duration"], 3),
                    "modified_duration": round(duration_data["modified_duration"], 3),
                    "convexity": round(duration_data["convexity"], 3),
                    "estimated_price": round(duration_data["price"], 2),
                    "valuation_date": today,
                },
                indent=2,
            )

        return input_table.select(
            result=pw.apply(calc_duration, pw.this.bond_identifier)
        )

    def register_mcp(self, server: McpServer):
        server.tool(
            "calculate_bond_duration",
            request_handler=self.handler,
            schema=BondDurationSchema,
        )


class FilterBondsTool(McpServable):
    """Filter bonds by criteria"""

    def handler(self, input_table):
        def filter_bonds(
            min_coupon, max_coupon, min_years, max_years, symbol_contains, name_contains
        ):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bonds_list = COMPUTED_DATA.get("bonds_list", [])
            criteria = {}
            if min_coupon > 0:
                criteria["min_coupon"] = min_coupon
            if max_coupon > 0:
                criteria["max_coupon"] = max_coupon
            if min_years > 0:
                criteria["min_years_to_maturity"] = min_years
            if max_years > 0:
                criteria["max_years_to_maturity"] = max_years
            if symbol_contains:
                criteria["symbol_contains"] = symbol_contains
            if name_contains:
                criteria["name_contains"] = name_contains

            filtered = filter_bonds_by_criteria(bonds_list, criteria)

            results = [
                {
                    "symbol": b["symbol"],
                    "name": b["name"],
                    "coupon_rate": round(b["coupon_rate"] * 100, 2),
                    "maturity_date": b["maturity_date"],
                }
                for b in filtered
            ]

            return json.dumps(
                {"total_matches": len(results), "criteria": criteria, "bonds": results},
                indent=2,
            )

        return input_table.select(
            result=pw.apply(
                filter_bonds,
                pw.this.min_coupon,
                pw.this.max_coupon,
                pw.this.min_years_to_maturity,
                pw.this.max_years_to_maturity,
                pw.this.symbol_contains,
                pw.this.name_contains,
            )
        )

    def register_mcp(self, server: McpServer):
        server.tool(
            "filter_bonds", request_handler=self.handler, schema=FilterBondsSchema
        )


class CompareBondsTo(McpServable):
    """Compare multiple bonds"""

    def handler(self, input_table):
        def compare(bond_identifiers):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            identifiers = [x.strip() for x in bond_identifiers.split(",")]
            forecast_df = COMPUTED_DATA["forecast_df"]

            if forecast_df is None:
                return json.dumps({"error": "No yield data available"})

            today = sorted(forecast_df["Target_Date"].unique())[0]
            day_data = forecast_df[forecast_df["Target_Date"] == today]

            curve_data = {}
            for _, row in day_data.iterrows():
                curve_data[float(row["Maturity"])] = (
                    float(row["Predicted_Yield"]) / 100.0
                )

            comparisons = []
            for identifier in identifiers:
                bond = get_bond_by_identifier(identifier)
                if not bond:
                    continue

                ytm = calculate_bond_ytm_today(bond, curve_data, today)
                if ytm is None:
                    continue

                duration_data = calculate_bond_duration_and_convexity(bond, ytm, today)
                if duration_data is None:
                    continue

                comparisons.append(
                    {
                        "symbol": bond["symbol"],
                        "name": bond["name"],
                        "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                        "ytm_percent": round(ytm * 100, 3),
                        "price": round(duration_data["price"], 2),
                        "duration": round(duration_data["modified_duration"], 3),
                        "convexity": round(duration_data["convexity"], 3),
                    }
                )

            return json.dumps(
                {
                    "comparison_date": today,
                    "bonds_compared": len(comparisons),
                    "bonds": comparisons,
                },
                indent=2,
            )

        return input_table.select(result=pw.apply(compare, pw.this.bond_identifiers))

    def register_mcp(self, server: McpServer):
        server.tool(
            "compare_bonds", request_handler=self.handler, schema=CompareBondsSchema
        )


class GetYieldCurveTool(McpServable):
    """Get yield curve for specific date"""

    def handler(self, input_table):
        def get_curve(days_ahead):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                return json.dumps({"error": "No forecast data"})

            unique_dates = sorted(forecast_df["Target_Date"].unique())
            if days_ahead <= 0 or days_ahead > len(unique_dates):
                target_date = unique_dates[0]
            else:
                target_date = unique_dates[days_ahead - 1]

            curve = get_yield_curve_for_date(forecast_df, target_date)
            if not curve:
                return json.dumps({"error": "Could not build yield curve"})

            curve_data = [
                {"maturity": f"{k}Y", "yield": round(v, 3)}
                for k, v in sorted(curve.items())
            ]

            return json.dumps(
                {"date": target_date, "yield_curve": curve_data}, indent=2
            )

        return input_table.select(result=pw.apply(get_curve, pw.this.days_ahead))

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_yield_curve", request_handler=self.handler, schema=YieldCurveDateSchema
        )


class RecommendBondsTool(McpServable):
    """Recommend bonds based on criteria"""

    def handler(self, input_table):
        def recommend(target_yield, max_risk, investment_horizon, sort_by):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bonds_list = COMPUTED_DATA.get("bonds_list", [])
            forecast_df = COMPUTED_DATA["forecast_df"]

            if forecast_df is None:
                return json.dumps({"error": "No yield data"})

            today = sorted(forecast_df["Target_Date"].unique())[0]
            curve_data = get_yield_curve_for_date(forecast_df, today)

            if not curve_data:
                return json.dumps({"error": "Cannot build yield curve"})

            curve_decimal = {k: v / 100.0 for k, v in curve_data.items()}

            criteria = {}
            if target_yield > 0:
                criteria["target_yield"] = target_yield
            if max_risk:
                criteria["max_risk"] = max_risk
            if investment_horizon > 0:
                criteria["investment_horizon"] = investment_horizon
            if sort_by:
                criteria["sort_by"] = sort_by

            recommendations = recommend_bonds_by_criteria(
                bonds_list, curve_decimal, today, criteria
            )

            results = []
            for rec in recommendations[:20]:
                bond = rec["bond"]
                results.append(
                    {
                        "symbol": bond["symbol"],
                        "name": bond["name"],
                        "ytm_percent": round(rec["ytm"], 3),
                        "estimated_price": round(rec["price"], 2),
                        "modified_duration": round(rec["duration"], 3),
                        "years_to_maturity": round(rec["years_to_maturity"], 2),
                        "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                        "maturity_date": bond["maturity_date"],
                    }
                )

            return json.dumps(
                {
                    "recommendation_date": today,
                    "total_recommendations": len(results),
                    "recommendations": results,
                },
                indent=2,
            )

        return input_table.select(
            result=pw.apply(
                recommend,
                pw.this.target_yield,
                pw.this.max_risk,
                pw.this.investment_horizon,
                pw.this.sort_by,
            )
        )

    def register_mcp(self, server: McpServer):
        server.tool(
            "recommend_bonds", request_handler=self.handler, schema=RecommendBondsSchema
        )


"""
Bond Forecasting Server - UPDATED to return LTP
Key change: GetBondDetailsTool now returns actual LTP from CSV
"""

# [All previous imports and configuration remain the same...]


class GetBondDetailsTool(McpServable):
    """Get comprehensive bond details including LTP and market data"""

    def handler(self, input_table):
        def get_details(bond_identifier):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bond = get_bond_by_identifier(bond_identifier)
            if not bond:
                return json.dumps({"error": f"Bond '{bond_identifier}' not found"})

            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                return json.dumps({"error": "No yield data available"})

            today = sorted(forecast_df["Target_Date"].unique())[0]
            day_data = forecast_df[forecast_df["Target_Date"] == today]

            curve_data = {}
            for _, row in day_data.iterrows():
                curve_data[float(row["Maturity"])] = (
                    float(row["Predicted_Yield"]) / 100.0
                )

            # Calculate all analytics
            ytm = calculate_bond_ytm_today(bond, curve_data, today)
            theoretical_price = price_bond_dirty_price(bond, curve_data, today)

            duration_data = None
            if ytm:
                duration_data = calculate_bond_duration_and_convexity(bond, ytm, today)

            maturity_date = datetime.strptime(bond["maturity_date"], "%Y-%m-%d")
            years_to_maturity = (maturity_date - datetime.now()).days / 365.25

            #  NEW: Get LTP from bond data
            ltp = bond.get("last_traded_price", None)

            result = {
                "isin": bond["isin"],
                "symbol": bond["symbol"],
                "name": bond["name"],
                "face_value": bond["face_value"],
                "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                "coupon_frequency": bond["coupon_frequency"],
                "maturity_date": bond["maturity_date"],
                "years_to_maturity": round(years_to_maturity, 2),
                #  NEW: Return both LTP and theoretical price
                "last_traded_price": round(ltp, 2)
                if ltp
                else None,  # Real market price
                "theoretical_price": round(theoretical_price, 2)
                if theoretical_price
                else None,  # Calculated
                "current_price": round(ltp, 2)
                if ltp
                else (
                    round(theoretical_price, 2) if theoretical_price else None
                ),  # Default to LTP
                "ytm": round(ytm * 100, 3) if ytm else None,
                "valuation_date": today,
            }

            if duration_data:
                result.update(
                    {
                        "macaulay_duration": round(
                            duration_data["macaulay_duration"], 3
                        ),
                        "modified_duration": round(
                            duration_data["modified_duration"], 3
                        ),
                        "convexity": round(duration_data["convexity"], 3),
                    }
                )

            return json.dumps(result, indent=2)

        return input_table.select(result=pw.apply(get_details, pw.this.bond_identifier))

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_bond_details",
            request_handler=self.handler,
            schema=BondIdentifierRequestSchema,
        )


class GetAllBondsAnalyticsTool(McpServable):
    """Get analytics for all bonds with LTP and yield curve data"""

    def handler(self, input_table):
        if not COMPUTED_DATA["ready"]:
            result = json.dumps({"status": "Data still loading..."})
        else:
            bonds_list = COMPUTED_DATA.get("bonds_list", [])
            forecast_df = COMPUTED_DATA["forecast_df"]

            if forecast_df is None:
                result = json.dumps({"error": "No yield data available"})
            else:
                today = sorted(forecast_df["Target_Date"].unique())[0]
                day_data = forecast_df[forecast_df["Target_Date"] == today]

                curve_data = {}
                for _, row in day_data.iterrows():
                    curve_data[float(row["Maturity"])] = (
                        float(row["Predicted_Yield"]) / 100.0
                    )

                analytics = []
                for bond in bonds_list:
                    ytm = calculate_bond_ytm_today(bond, curve_data, today)
                    theoretical_price = price_bond_dirty_price(bond, curve_data, today)

                    if ytm is None:
                        continue

                    duration_data = calculate_bond_duration_and_convexity(
                        bond, ytm, today
                    )
                    if duration_data is None:
                        continue

                    maturity_date = datetime.strptime(bond["maturity_date"], "%Y-%m-%d")
                    years_to_maturity = (maturity_date - datetime.now()).days / 365.25

                    #  NEW: Include LTP
                    ltp = bond.get("last_traded_price", None)
                    current_price = ltp if ltp else theoretical_price

                    analytics.append(
                        {
                            "isin": bond["isin"],
                            "symbol": bond["symbol"],
                            "name": bond["name"],
                            "coupon_rate": round(bond["coupon_rate"] * 100, 2),
                            "years_to_maturity": round(years_to_maturity, 2),
                            "last_traded_price": round(ltp, 2) if ltp else None,
                            "theoretical_price": round(theoretical_price, 2)
                            if theoretical_price
                            else None,
                            "current_price": round(current_price, 2)
                            if current_price
                            else None,
                            "ytm": round(ytm * 100, 3),
                            "modified_duration": round(
                                duration_data["modified_duration"], 3
                            ),
                            "convexity": round(duration_data["convexity"], 3),
                        }
                    )

                result = json.dumps(
                    {
                        "valuation_date": today,
                        "total_bonds": len(analytics),
                        "bonds_with_ltp": len(
                            [a for a in analytics if a.get("last_traded_price")]
                        ),
                        "analytics": analytics,
                    },
                    indent=2,
                )

        return input_table.select(result=result)

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_all_bonds_analytics", request_handler=self.handler, schema=EmptySchema
        )


class BatchBondPricingTool(McpServable):
    """Get pricing for multiple bonds at once with LTP"""

    def handler(self, input_table):
        def batch_price(bond_identifiers, days_ahead):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            identifiers = [x.strip() for x in bond_identifiers.split(",")]
            forecast_df = COMPUTED_DATA["forecast_df"]

            if forecast_df is None:
                return json.dumps({"error": "No yield data available"})

            unique_dates = sorted(forecast_df["Target_Date"].unique())

            if days_ahead > 0 and days_ahead <= len(unique_dates):
                target_date = unique_dates[days_ahead - 1]
            else:
                target_date = unique_dates[0]

            day_data = forecast_df[forecast_df["Target_Date"] == target_date]

            curve_data = {}
            for _, row in day_data.iterrows():
                curve_data[float(row["Maturity"])] = (
                    float(row["Predicted_Yield"]) / 100.0
                )

            results = []
            for identifier in identifiers:
                bond = get_bond_by_identifier(identifier)
                if not bond:
                    continue

                ytm = calculate_bond_ytm_today(bond, curve_data, target_date)
                theoretical_price = price_bond_dirty_price(
                    bond, curve_data, target_date
                )

                if ytm is None:
                    continue

                duration_data = calculate_bond_duration_and_convexity(
                    bond, ytm, target_date
                )

                #  NEW: Include LTP for day 0
                ltp = bond.get("last_traded_price", None) if days_ahead == 0 else None
                display_price = ltp if (days_ahead == 0 and ltp) else theoretical_price

                result = {
                    "isin": bond["isin"],
                    "symbol": bond["symbol"],
                    "name": bond["name"],
                    "price": round(display_price, 2) if display_price else None,
                    "ytm": round(ytm * 100, 3),
                }

                if days_ahead == 0 and ltp:
                    result["last_traded_price"] = round(ltp, 2)
                    result["theoretical_price"] = (
                        round(theoretical_price, 2) if theoretical_price else None
                    )

                if duration_data:
                    result.update(
                        {
                            "duration": round(duration_data["modified_duration"], 3),
                            "convexity": round(duration_data["convexity"], 3),
                        }
                    )

                results.append(result)

            return json.dumps(
                {
                    "valuation_date": target_date,
                    "days_ahead": days_ahead,
                    "bonds_priced": len(results),
                    "results": results,
                },
                indent=2,
            )

        return input_table.select(
            result=pw.apply(batch_price, pw.this.bond_identifiers, pw.this.days_ahead)
        )

    def register_mcp(self, server: McpServer):
        server.tool(
            "batch_bond_pricing",
            request_handler=self.handler,
            schema=CompareBondsSchema,
        )


class GetRiskMetricsTool(McpServable):
    """Calculate comprehensive risk metrics for a bond"""

    def handler(self, input_table):
        def get_risk_metrics(bond_identifier):
            if not COMPUTED_DATA["ready"]:
                return json.dumps({"status": "Data still loading..."})

            bond = get_bond_by_identifier(bond_identifier)
            if not bond:
                return json.dumps({"error": f"Bond '{bond_identifier}' not found"})

            forecast_df = COMPUTED_DATA["forecast_df"]
            if forecast_df is None:
                return json.dumps({"error": "No yield data available"})

            today = sorted(forecast_df["Target_Date"].unique())[0]
            day_data = forecast_df[forecast_df["Target_Date"] == today]

            curve_data = {}
            for _, row in day_data.iterrows():
                curve_data[float(row["Maturity"])] = (
                    float(row["Predicted_Yield"]) / 100.0
                )

            ytm = calculate_bond_ytm_today(bond, curve_data, today)
            if ytm is None:
                return json.dumps({"error": "Could not calculate YTM"})

            duration_data = calculate_bond_duration_and_convexity(bond, ytm, today)
            if duration_data is None:
                return json.dumps({"error": "Could not calculate risk metrics"})

            # Calculate additional risk metrics
            mod_duration = duration_data["modified_duration"]
            convexity = duration_data["convexity"]
            price = duration_data["price"]

            # Rate sensitivity (price change for 1% rate change)
            rate_sensitivity_1pct = -mod_duration * price * 0.01

            # Convexity adjustment for 1% rate change
            convexity_adj_1pct = 0.5 * convexity * price * (0.01**2)

            # Total price change including convexity
            total_price_change_1pct = rate_sensitivity_1pct + convexity_adj_1pct

            # Risk classification
            if mod_duration > 7:
                risk_class = "High"
            elif mod_duration > 4:
                risk_class = "Medium"
            else:
                risk_class = "Low"

            return json.dumps(
                {
                    "bond_symbol": bond["symbol"],
                    "bond_name": bond["name"],
                    "current_price": round(price, 2),
                    "ytm_percent": round(ytm * 100, 3),
                    "macaulay_duration": round(duration_data["macaulay_duration"], 3),
                    "modified_duration": round(mod_duration, 3),
                    "convexity": round(convexity, 3),
                    "rate_sensitivity_1pct": round(rate_sensitivity_1pct, 2),
                    "convexity_adjustment_1pct": round(convexity_adj_1pct, 2),
                    "total_price_change_1pct": round(total_price_change_1pct, 2),
                    "risk_classification": risk_class,
                    "is_rate_sensitive": mod_duration > 7,
                    "valuation_date": today,
                },
                indent=2,
            )

        return input_table.select(
            result=pw.apply(get_risk_metrics, pw.this.bond_identifier)
        )

    def register_mcp(self, server: McpServer):
        server.tool(
            "get_risk_metrics",
            request_handler=self.handler,
            schema=BondIdentifierRequestSchema,
        )


# ==================== MAIN SERVER ====================


def run_server():
    """Main server execution - COMPUTE FIRST, then start MCP, then enable daily updates"""
    print("\n" + "=" * 80)
    print("BOND FORECASTING SERVER - STATIC MODE WITH DAILY UPDATES")
    print("=" * 80 + "\n")

    # 1. COMPUTE ALL DATA FIRST
    if not compute_all_data():
        print("\n Failed to compute data. Exiting.")
        return

    # 3. NOW START MCP SERVER
    print("=" * 80)
    print("STARTING MCP SERVER")
    print("=" * 80 + "\n")

    try:
        server = PathwayMcp(
            host=MCP_HOST,
            port=MCP_PORT,
            name="BondAnalystPro",
            serve=[
                LatestYieldsTool(),
                AllForecastsTool(),
                YieldForecastTool(),
                ListBondsTool(),
                SearchBondsTool(),
                BondInfoTool(),
                BondPriceBySymbolTool(),
                CalculateBondYTMTool(),
                CalculateBondDurationTool(),
                FilterBondsTool(),
                CompareBondsTo(),
                GetYieldCurveTool(),
                RecommendBondsTool(),
                GetBondDetailsTool(),
                GetAllBondsAnalyticsTool(),
                BatchBondPricingTool(),
                GetRiskMetricsTool(),
            ],
        )

        print(f" MCP Server running at: http://{MCP_HOST}:{MCP_PORT}/")
        print(f"\n Server Status:")
        print(f"   - Maturities loaded: {list(COMPUTED_DATA['latest_yields'].keys())}")
        print(f"   - Forecast rows: {len(COMPUTED_DATA['forecast_df'])}")
        print(f"   - Bonds available: {len(COMPUTED_DATA['bonds_list'])}")
        print(
            f"   - Last update: {COMPUTED_DATA['last_update'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"\n Daily Updates:")
        print(
            f"   - Next recomputation: {(datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"\n Server is ready to accept requests!")
        print("Press Ctrl+C to stop")
        print("=" * 80 + "\n")

        # Run empty pathway to keep server alive
        pw.run(monitoring_level=pw.MonitoringLevel.NONE, terminate_on_error=True)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("SHUTDOWN")
        print("=" * 80)
        print(" Server stopped gracefully")

    except Exception as e:
        print(f"\n FATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        run_server()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import sys

        sys.exit(1)
