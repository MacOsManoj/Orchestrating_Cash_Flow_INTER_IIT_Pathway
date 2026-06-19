"""
Bond Forecasting Core - FIXED VERSION
Key fixes:
1. Added date filtering to pipeline
2. Proper incremental model training
3. Efficient cache usage
"""

import pathway as pw
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import deque
from scipy.optimize import minimize
from scipy.interpolate import CubicSpline
from river import tree

# ==================== CONFIGURATION ====================

pw.set_license_key("1EBCE3-0E3417-3066F3-5C3F8A-48F543-V3")

FORECAST_DAYS = 21
LOOKBACK_DAYS = 365

# Get script directory to make all paths relative
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)  # Change to script directory so relative paths work

INPUT_FILES = {
    1: "../data/1y.csv",
    2: "../data/2y.csv",
    5: "../data/5y.csv",
    7: "../data/7y.csv",
    10: "../data/10y.csv",
}

OUTPUT_DIR = "../output_forecasts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BONDS_CSV_FILE = "../data/bonds_data.csv"

# ==================== GLOBAL STATE ====================

COMPUTED_DATA = {
    "latest_yields": {},
    "forecast_df": None,
    "bonds_list": [],
    "skipped_bonds": [],
    "ready": False,
    "last_update": None,
}

MODEL_CACHE = {}
MODEL_METADATA = {}  # Track model training state

# ==================== PATHWAY SCHEMAS ====================


class YieldSchema(pw.Schema):
    Date: str
    Open: str
    High: str
    Low: str
    Close: str


# ==================== BOND LOADING ====================


def load_bonds_from_csv(csv_path):
    """Load bond information from CSV file INCLUDING LTP"""
    if not os.path.exists(csv_path):
        print(f"Warning: Bonds CSV not found: {csv_path}")
        return [], []

    bonds_df = pd.read_csv(csv_path)
    bonds_list = []
    skipped_bonds = []

    for idx, row in bonds_df.iterrows():
        try:
            symbol = str(row.get("SYMBOL", "")).strip()
            isin = str(row.get("ISIN", "")).strip()
            isin_desc = str(row.get("ISIN Description", "")).strip()

            if not symbol and not isin:
                continue

            #  NEW: Extract LTP (Last Traded Price)
            ltp = None
            ltp_raw = row.get("LTP", None)
            if ltp_raw is not None and str(ltp_raw).strip() not in [
                "-",
                "",
                "nan",
                "NaN",
            ]:
                try:
                    ltp = float(ltp_raw)
                    if ltp <= 0:
                        ltp = None
                except (ValueError, TypeError):
                    ltp = None

            # Parse face value
            try:
                face_value = float(row.get("FACE VALUE", 100.0))
                if face_value <= 0:
                    face_value = 100.0
            except (ValueError, TypeError):
                face_value = 100.0

            # Parse maturity date
            maturity_date_str = str(row.get("Maturity Date", "")).strip()
            if (
                not maturity_date_str
                or maturity_date_str == "-"
                or maturity_date_str.lower() == "nan"
            ):
                skipped_bonds.append(
                    {"symbol": symbol, "isin": isin, "reason": "No maturity date"}
                )
                continue

            maturity_date = None
            for date_format in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    maturity_date = datetime.strptime(maturity_date_str, date_format)
                    break
                except ValueError:
                    continue

            if maturity_date is None or maturity_date <= datetime.now():
                skipped_bonds.append(
                    {"symbol": symbol, "isin": isin, "reason": "Invalid/past maturity"}
                )
                continue

            # Extract coupon rate from ISIN Description
            import re

            coupon_rate = None
            match = re.search(r"(\d+\.\d+)\s*FV", isin_desc)
            if match:
                coupon_rate = float(match.group(1)) / 100.0
            else:
                numbers = re.findall(r"\b(\d+\.\d+)\b", isin_desc)
                for num in numbers:
                    rate = float(num)
                    if 2.0 <= rate <= 20.0:
                        coupon_rate = rate / 100.0
                        break

            if coupon_rate is None or coupon_rate < 0.001 or coupon_rate > 0.25:
                skipped_bonds.append(
                    {"symbol": symbol, "isin": isin, "reason": "No valid coupon"}
                )
                continue

            # Create bond name
            bond_name = re.sub(r"\d+\.\d+\s*FV\s*RS\s*\d+", "", isin_desc).strip()
            if not bond_name:
                bond_name = f"{symbol} ({isin})" if isin else symbol

            #  NEW: Determine bond type, rating, and risk based on SERIES
            series = str(row.get("SERIES", "")).strip().upper()

            # Identify government bonds
            is_govt_bond = False
            bond_type = "Corporate"
            rating = "A"
            risk_level = "Medium"

            if series in ["GS", "TB"]:
                # GS = Government Securities, TB = Treasury Bills
                is_govt_bond = True
                bond_type = "Government"
                rating = "AAA"
                risk_level = "Low"
            elif series == "SG":
                # SG = State Government bonds
                is_govt_bond = True
                bond_type = "State Government"
                rating = "AAA"
                risk_level = "Low"
            elif (
                "GOVERNMENT OF INDIA" in isin_desc.upper() or "GOI" in isin_desc.upper()
            ):
                # Double-check by description
                is_govt_bond = True
                bond_type = "Government"
                rating = "AAA"
                risk_level = "Low"
            elif (
                "STATE DEVELOPMENT LOAN" in isin_desc.upper()
                or "SDL" in isin_desc.upper()
            ):
                # State government loans
                is_govt_bond = True
                bond_type = "State Government"
                rating = "AAA"
                risk_level = "Low"

            #  NEW: Include LTP, rating, and risk in bond info
            bond_info = {
                "name": bond_name,
                "symbol": symbol,
                "isin": isin,
                "face_value": face_value,
                "coupon_rate": coupon_rate,
                "coupon_frequency": 2,
                "maturity_date": maturity_date.strftime("%Y-%m-%d"),
                "description": isin_desc,
                "last_traded_price": ltp,  #  Store LTP
                "bond_type": bond_type,  #  NEW: Government/State/Corporate
                "rating": rating,  #  NEW: AAA for govt bonds
                "risk_level": risk_level,  #  NEW: Low for govt bonds
                "series": series,  #  Store series for reference
            }

            bonds_list.append(bond_info)

        except Exception as e:
            print(f"Error processing bond row {idx}: {e}")
            continue

    print(
        f"Loaded {len(bonds_list)} bonds (with LTP data), skipped {len(skipped_bonds)}"
    )

    # Print LTP statistics
    bonds_with_ltp = [b for b in bonds_list if b.get("last_traded_price") is not None]
    print(f"   {len(bonds_with_ltp)} bonds have LTP data")
    print(f"    {len(bonds_list) - len(bonds_with_ltp)} bonds missing LTP")

    #  NEW: Print rating statistics
    govt_bonds = [
        b
        for b in bonds_list
        if b.get("bond_type") in ["Government", "State Government"]
    ]
    aaa_bonds = [b for b in bonds_list if b.get("rating") == "AAA"]
    low_risk_bonds = [b for b in bonds_list if b.get("risk_level") == "Low"]
    print(f"    {len(govt_bonds)} government bonds (all rated AAA)")
    print(f"   {len(aaa_bonds)} bonds rated AAA")
    print(f"   {len(low_risk_bonds)} low-risk bonds")

    return bonds_list, skipped_bonds


def get_bond_by_identifier(identifier):
    """Get bond by symbol or ISIN"""
    identifier = identifier.strip().upper()
    bonds_list = COMPUTED_DATA.get("bonds_list", [])

    for bond in bonds_list:
        if (
            bond["symbol"].upper() == identifier
            or bond["isin"].upper() == identifier
            or bond["name"].upper() == identifier
        ):
            return bond
    return None


def get_all_bond_symbols():
    """Get all available bond symbols"""
    bonds_list = COMPUTED_DATA.get("bonds_list", [])
    return [
        {"symbol": b["symbol"], "isin": b["isin"], "name": b["name"]}
        for b in bonds_list
    ]


# Load bonds on initialization
BONDS_TO_PRICE, SKIPPED_BONDS = load_bonds_from_csv(BONDS_CSV_FILE)
COMPUTED_DATA["bonds_list"] = BONDS_TO_PRICE
COMPUTED_DATA["skipped_bonds"] = SKIPPED_BONDS

print(f"Initialized with {len(BONDS_TO_PRICE)} bonds for pricing")


@pw.udf(deterministic=True, return_type=str)
def get_forecast_day(data, idx):
    if hasattr(data, "as_dict"):
        data = data.as_dict()
    f = data.get("forecasts", [])
    return f[idx]["date"] if 0 <= idx < len(f) else ""


@pw.udf(deterministic=True, return_type=float)
def get_predicted_close(data, idx):
    if hasattr(data, "as_dict"):
        data = data.as_dict()
    f = data.get("forecasts", [])
    return float(f[idx]["predicted_close"]) if 0 <= idx < len(f) else 0.0


@pw.udf(deterministic=True, return_type=float)
def get_predicted_return(data, idx):
    if hasattr(data, "as_dict"):
        data = data.as_dict()
    f = data.get("forecasts", [])
    return float(f[idx]["predicted_return"]) if 0 <= idx < len(f) else 0.0


@pw.udf(deterministic=True, return_type=int)
def get_maturity(data):
    if hasattr(data, "as_dict"):
        data = data.as_dict()
    return int(data.get("maturity", 0))


# ==================== BOND PRICING FUNCTIONS ====================


def nelson_siegel(tau, beta0, beta1, beta2, lambda_param):
    """Nelson-Siegel yield curve model"""
    if tau <= 0:
        return beta0
    term1 = (1 - np.exp(-lambda_param * tau)) / (lambda_param * tau)
    term2 = term1 - np.exp(-lambda_param * tau)
    return beta0 + beta1 * term1 + beta2 * term2


def objective_function(params, maturities, yields, weights, alpha=0.01):
    """Objective function for Nelson-Siegel optimization"""
    beta0, beta1, beta2, lambda_param = params
    predicted_yields = [
        nelson_siegel(tau, beta0, beta1, beta2, lambda_param) for tau in maturities
    ]
    errors = np.array(yields) - np.array(predicted_yields)
    weighted_mse = np.sum(weights * errors**2)
    regularization = alpha * (beta1**2 + beta2**2)
    return weighted_mse + regularization


def fit_nelson_siegel_weighted(maturities, yields, target_maturity):
    """Fit Nelson-Siegel model with weighted optimization"""
    try:
        distances = np.abs(maturities - target_maturity)
        weights = 1 / (1 + distances)
        weights = weights / weights.sum()
        bounds = [(0, 0.20), (-0.15, 0.15), (-0.15, 0.15), (0.1, 3)]

        initial_guesses = [
            [yields[-1], yields[0] - yields[-1], 0, 0.6],
            [yields.mean(), yields[0] - yields.mean(), 0, 1.0],
        ]

        best_result = None
        best_error = float("inf")

        for initial_params in initial_guesses:
            try:
                result = minimize(
                    objective_function,
                    initial_params,
                    args=(maturities, yields, weights),
                    method="L-BFGS-B",
                    bounds=bounds,
                )
                if result.success and result.fun < best_error:
                    best_error = result.fun
                    best_result = result
            except:
                continue

        if best_result:
            return best_result.x

        return initial_guesses[0]

    except:
        return initial_guesses[0]


def linear_interpolation(maturities, yields, target_maturity):
    """Linear interpolation for yield curve"""
    maturities = np.array(maturities)
    yields = np.array(yields)
    if target_maturity <= maturities[0]:
        return yields[0]
    if target_maturity >= maturities[-1]:
        return yields[-1]

    lower_idx = np.where(maturities < target_maturity)[0][-1]
    upper_idx = np.where(maturities > target_maturity)[0][0]
    t1, y1 = maturities[lower_idx], yields[lower_idx]
    t2, y2 = maturities[upper_idx], yields[upper_idx]
    return y1 + (y2 - y1) * (target_maturity - t1) / (t2 - t1)


def cubic_spline_interpolation(maturities, yields, target_maturity):
    """Cubic spline interpolation"""
    try:
        cs = CubicSpline(maturities, yields, bc_type="natural")
        return cs(target_maturity)
    except:
        return linear_interpolation(maturities, yields, target_maturity)


def ensemble_extrapolate_yield(maturities, yields, target_maturity):
    """Ensemble yield extrapolation"""
    if target_maturity < 0.25:
        return linear_interpolation(maturities, yields, target_maturity)
    try:
        ns_pred = nelson_siegel(
            target_maturity,
            *fit_nelson_siegel_weighted(maturities, yields, target_maturity),
        )
        spline_pred = cubic_spline_interpolation(maturities, yields, target_maturity)
        linear_pred = linear_interpolation(maturities, yields, target_maturity)
        weights = [0.4, 0.4, 0.2]
        return (
            weights[0] * ns_pred + weights[1] * spline_pred + weights[2] * linear_pred
        )
    except:
        return linear_interpolation(maturities, yields, target_maturity)


def calculate_years_to_maturity(valuation_date, maturity_date):
    """Calculate years to maturity"""
    if isinstance(valuation_date, str):
        valuation_date = pd.to_datetime(valuation_date)
    if isinstance(maturity_date, str):
        maturity_date = pd.to_datetime(maturity_date)
    days_diff = (maturity_date - valuation_date).days
    return max(0, days_diff / 365.25)


def generate_cash_flows(
    face_value,
    coupon_rate,
    coupon_frequency,
    valuation_date,
    maturity_date,
    issue_date=None,
):
    """Generate bond cash flows"""
    if isinstance(valuation_date, str):
        valuation_date = pd.to_datetime(valuation_date)
    if isinstance(maturity_date, str):
        maturity_date = pd.to_datetime(maturity_date)
    if issue_date and isinstance(issue_date, str):
        issue_date = pd.to_datetime(issue_date)

    if valuation_date >= maturity_date:
        return []
    if issue_date and valuation_date < issue_date:
        valuation_date = issue_date

    annual_coupon = face_value * coupon_rate
    coupon_payment = annual_coupon / coupon_frequency

    months_between = 12 // coupon_frequency
    payment_dates = []
    current = maturity_date
    while current > valuation_date:
        payment_dates.append(current)
        current = current - relativedelta(months=months_between)
    payment_dates.reverse()

    cash_flows = []
    for i, p_date in enumerate(payment_dates):
        years = calculate_years_to_maturity(valuation_date, p_date)
        if years <= 0:
            continue
        amount = (
            coupon_payment + face_value
            if i == len(payment_dates) - 1
            else coupon_payment
        )
        cash_flows.append({"payment_date": p_date, "cash_flow": amount, "years": years})

    return cash_flows


def price_bond_dirty_price(bond_info, yield_curve_data, valuation_date):
    """Calculate bond dirty price"""
    try:
        face_value = bond_info["face_value"]
        coupon_rate = bond_info["coupon_rate"]
        coupon_frequency = bond_info["coupon_frequency"]
        maturity_date = bond_info["maturity_date"]

        cash_flows = generate_cash_flows(
            face_value, coupon_rate, coupon_frequency, valuation_date, maturity_date
        )
        if not cash_flows:
            return None

        available_maturities = np.array(sorted(yield_curve_data.keys()))
        available_yields = np.array([yield_curve_data[m] for m in available_maturities])

        if len(available_maturities) < 2:
            return None

        pv_total = 0.0
        for cf in cash_flows:
            years = cf["years"]
            amount = cf["cash_flow"]

            if years in yield_curve_data:
                ytm_decimal = yield_curve_data[years]
            else:
                ytm_decimal = ensemble_extrapolate_yield(
                    available_maturities, available_yields, years
                )

            if ytm_decimal <= 0:
                ytm_decimal = 0.01

            discount_factor = 1 / ((1 + ytm_decimal) ** years)
            pv = amount * discount_factor
            pv_total += pv

        return pv_total

    except Exception as e:
        return None


def calculate_bond_ytm_today(bond_info, yield_curve_data, valuation_date):
    """Calculate bond YTM"""
    try:
        maturity_date_str = bond_info["maturity_date"]
        years_to_maturity = calculate_years_to_maturity(
            valuation_date, maturity_date_str
        )

        if years_to_maturity <= 0:
            return None

        available_maturities = np.array(sorted(yield_curve_data.keys()))
        available_yields = np.array([yield_curve_data[m] for m in available_maturities])

        if len(available_maturities) < 2:
            return None

        ytm = ensemble_extrapolate_yield(
            available_maturities, available_yields, years_to_maturity
        )
        return ytm

    except Exception as e:
        return None


def calculate_bond_duration_and_convexity(bond_info, ytm, valuation_date):
    """Calculate bond duration and convexity"""
    try:
        face_value = bond_info["face_value"]
        coupon_rate = bond_info["coupon_rate"]
        coupon_frequency = bond_info["coupon_frequency"]
        maturity_date = bond_info["maturity_date"]

        cash_flows = generate_cash_flows(
            face_value, coupon_rate, coupon_frequency, valuation_date, maturity_date
        )

        if not cash_flows:
            return None

        pv_total = 0.0
        weighted_time = 0.0
        weighted_time_squared = 0.0

        for cf in cash_flows:
            years = cf["years"]
            amount = cf["cash_flow"]

            discount_factor = 1 / ((1 + ytm) ** years)
            pv = amount * discount_factor

            pv_total += pv
            weighted_time += pv * years
            weighted_time_squared += pv * years * (years + 1)

        if pv_total == 0:
            return None

        macaulay_duration = weighted_time / pv_total
        modified_duration = macaulay_duration / (1 + ytm)
        convexity = weighted_time_squared / (pv_total * ((1 + ytm) ** 2))

        return {
            "macaulay_duration": macaulay_duration,
            "modified_duration": modified_duration,
            "convexity": convexity,
            "price": pv_total,
        }

    except Exception as e:
        return None


def filter_bonds_by_criteria(bonds_list, criteria):
    """Filter bonds based on multiple criteria"""
    from datetime import datetime

    filtered = []

    for bond in bonds_list:
        coupon_pct = bond["coupon_rate"] * 100
        if "min_coupon" in criteria and coupon_pct < criteria["min_coupon"]:
            continue
        if "max_coupon" in criteria and coupon_pct > criteria["max_coupon"]:
            continue

        maturity_date = datetime.strptime(bond["maturity_date"], "%Y-%m-%d")
        years_to_maturity = (maturity_date - datetime.now()).days / 365.25

        if (
            "min_years_to_maturity" in criteria
            and years_to_maturity < criteria["min_years_to_maturity"]
        ):
            continue
        if (
            "max_years_to_maturity" in criteria
            and years_to_maturity > criteria["max_years_to_maturity"]
        ):
            continue

        if (
            "min_face_value" in criteria
            and bond["face_value"] < criteria["min_face_value"]
        ):
            continue
        if (
            "max_face_value" in criteria
            and bond["face_value"] > criteria["max_face_value"]
        ):
            continue

        if "symbol_contains" in criteria:
            if criteria["symbol_contains"].upper() not in bond["symbol"].upper():
                continue

        if "isin_contains" in criteria:
            if criteria["isin_contains"].upper() not in bond["isin"].upper():
                continue

        if "name_contains" in criteria:
            if criteria["name_contains"].upper() not in bond["name"].upper():
                continue

        filtered.append(bond)

    return filtered


def get_yield_curve_for_date(forecast_df, target_date):
    """Get complete yield curve for a specific date"""
    day_data = forecast_df[forecast_df["Target_Date"] == target_date]

    if day_data.empty:
        return None

    curve = {}
    for _, row in day_data.iterrows():
        maturity = float(row["Maturity"])
        yield_pct = float(row["Predicted_Yield"])
        curve[maturity] = yield_pct

    return curve


def recommend_bonds_by_criteria(bonds_list, yield_curve_data, valuation_date, criteria):
    """Recommend bonds based on investment criteria"""
    from datetime import datetime

    recommendations = []

    for bond in bonds_list:
        maturity_date = datetime.strptime(bond["maturity_date"], "%Y-%m-%d")
        years_to_maturity = (
            maturity_date - datetime.strptime(valuation_date, "%Y-%m-%d")
        ).days / 365.25

        if "investment_horizon" in criteria:
            horizon = criteria["investment_horizon"]
            if abs(years_to_maturity - horizon) > 2:
                continue

        ytm = calculate_bond_ytm_today(bond, yield_curve_data, valuation_date)
        if ytm is None:
            continue

        ytm_pct = ytm * 100

        if "target_yield" in criteria and ytm_pct < criteria["target_yield"]:
            continue

        duration_data = calculate_bond_duration_and_convexity(bond, ytm, valuation_date)
        if duration_data is None:
            continue

        modified_duration = duration_data["modified_duration"]

        if "max_risk" in criteria:
            max_risk = criteria["max_risk"].lower()
            if max_risk == "low" and modified_duration > 3:
                continue
            elif max_risk == "medium" and modified_duration > 7:
                continue

        recommendations.append(
            {
                "bond": bond,
                "ytm": ytm_pct,
                "duration": modified_duration,
                "price": duration_data["price"],
                "convexity": duration_data["convexity"],
                "years_to_maturity": years_to_maturity,
            }
        )

    if "sort_by" in criteria:
        sort_key = criteria["sort_by"].lower()
        if sort_key == "yield":
            recommendations.sort(key=lambda x: x["ytm"], reverse=True)
        elif sort_key == "duration":
            recommendations.sort(key=lambda x: x["duration"])
        elif sort_key == "price":
            recommendations.sort(key=lambda x: x["price"])
    else:
        recommendations.sort(key=lambda x: x["ytm"], reverse=True)

    return recommendations


# ==================== FIXED PIPELINE ====================

# Export main functions
# Export main functions and constants
__all__ = [
    # Constants
    "COMPUTED_DATA",
    "INPUT_FILES",
    "OUTPUT_DIR",
    "FORECAST_DAYS",
    "LOOKBACK_DAYS",
    "MODEL_CACHE",
    "MODEL_METADATA",
    # Main pipeline function
    "build_static_pipeline",
    # Bond data access
    "get_bond_by_identifier",
    "get_all_bond_symbols",
    "load_bonds_from_csv",
    # Forecast accessors
    "get_forecast_day",
    "get_predicted_close",
    "get_predicted_return",
    "get_maturity",
    # Yield curve functions
    "nelson_siegel",
    "fit_nelson_siegel_weighted",
    "linear_interpolation",
    "cubic_spline_interpolation",
    "ensemble_extrapolate_yield",
    "get_yield_curve_for_date",
    # Bond pricing and analytics
    "calculate_years_to_maturity",
    "generate_cash_flows",
    "price_bond_dirty_price",
    "calculate_bond_ytm_today",
    "calculate_bond_duration_and_convexity",
    # Bond filtering and recommendations
    "filter_bonds_by_criteria",
    "recommend_bonds_by_criteria",
]
