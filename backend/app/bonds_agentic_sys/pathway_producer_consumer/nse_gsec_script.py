import requests
import time
import json
import pandas as pd
from bs4 import BeautifulSoup
import re
from pathlib import Path
import urllib3
import numpy as np
import os
import logging
import sys
import schedule
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from scipy.optimize import minimize
from scipy.interpolate import CubicSpline

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== SETUP ====================
# Get script directory to make all paths relative
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)  # Change to script directory so relative paths work

OUTPUT_DIR = "../output_forecasts"
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Ensure output directory exists
FORECAST_FILE = os.path.join(OUTPUT_DIR, "final_forecasts.csv")
BONDS_FILE = os.path.join(OUTPUT_DIR, "bond_snapshot.csv")
HISTORICAL_BONDS_FILE = os.path.join(OUTPUT_DIR, "historical_bonds_data.csv")


def extract_maturity_from_description(description):
    """
    Extract maturity date from ISIN description
    Supports multiple formats:
    - 2-letter month + 2-digit year: 22JU45 -> 2045-06-22
    - 3-letter month + 2-digit year: 22JUN45 -> 2045-06-22
    - 3-letter month + 4-digit year: 02JAN2026 -> 2026-01-02
    """

    # Try 3-letter month + 4-digit year first (e.g., 02JAN2026)
    pattern_full = r"\b(\d{2})([A-Z]{3})(\d{4})\b"
    match = re.search(pattern_full, description)

    if match:
        day = match.group(1)
        month_abbr = match.group(2)
        year = match.group(3)  # Already 4 digits

        # Convert 3-letter month abbreviation to month number
        month_map = {
            "JAN": "01",
            "FEB": "02",
            "MAR": "03",
            "APR": "04",
            "MAY": "05",
            "JUN": "06",
            "JUL": "07",
            "AUG": "08",
            "SEP": "09",
            "OCT": "10",
            "NOV": "11",
            "DEC": "12",
        }

        month = month_map.get(month_abbr, "00")
        formatted_date = f"{year}-{month}-{day}"

        return formatted_date, match.group(0)

    # Try 2-letter month + 2-digit year (e.g., 22JU45)
    pattern_2 = r"\b(\d{2})([A-Z]{2})(\d{2})\b"
    match = re.search(pattern_2, description)

    if match:
        day = match.group(1)
        month_abbr = match.group(2)
        year = match.group(3)

        # Convert 2-letter month abbreviation to month number
        month_map = {
            "JN": "01",  # January (sometimes used)
            "FB": "02",  # February
            "MR": "03",  # March
            "AP": "04",  # April
            "MY": "05",  # May
            "JU": "06",  # June (also July in some cases)
            "JL": "07",  # July
            "AG": "08",  # August
            "SP": "09",  # September
            "OT": "10",  # October
            "NV": "11",  # November
            "DC": "12",  # December
        }

        month = month_map.get(month_abbr, "00")
        full_year = f"20{year}"
        formatted_date = f"{full_year}-{month}-{day}"

        return formatted_date, match.group(0)

    # Try 3-letter month + 2-digit year (e.g., 22JUN45)
    pattern_3 = r"\b(\d{2})([A-Z]{3})(\d{2})\b"
    match = re.search(pattern_3, description)

    if match:
        day = match.group(1)
        month_abbr = match.group(2)
        year = match.group(3)

        # Convert 3-letter month abbreviation to month number
        month_map = {
            "JAN": "01",
            "FEB": "02",
            "MAR": "03",
            "APR": "04",
            "MAY": "05",
            "JUN": "06",
            "JUL": "07",
            "AUG": "08",
            "SEP": "09",
            "OCT": "10",
            "NOV": "11",
            "DEC": "12",
        }

        month = month_map.get(month_abbr, "00")
        full_year = f"20{year}"
        formatted_date = f"{full_year}-{month}-{day}"

        return formatted_date, match.group(0)

    return None, None


def fetch_isin_data(isin):
    """Fetch bond data from NSDL by ISIN - returns all data like output.csv"""
    url = f"https://nsdl.co.in/master_search_detail_res.php?isin={isin}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # Disable SSL verification
        response = requests.get(url, headers=headers, timeout=10, verify=False)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            for td in soup.find_all("td", class_="tableheader"):
                if "ISIN Description" in td.get_text():
                    description_td = td.find_next_sibling("td")
                    if description_td:
                        description = description_td.get_text(strip=True)
                        maturity_date, raw_date = extract_maturity_from_description(
                            description
                        )

                        if maturity_date:
                            return maturity_date, raw_date, description, None
                        else:
                            return (
                                None,
                                None,
                                description,
                                "Date pattern not found in description",
                            )

            return None, None, None, "ISIN Description not found on page"
        else:
            return None, None, None, f"HTTP {response.status_code}"

    except Exception as e:
        return None, None, None, str(e)[:100]


def step1_fetch_nse_bonds():
    """Step 1: Fetch bonds data from NSE API"""
    print("=" * 60)
    print("STEP 1: Fetching NSE Bonds Data")
    print("=" * 60)

    url = "https://www.nseindia.com/api/liveBonds-traded-on-cm?type=gsec"

    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "referer": "https://www.nseindia.com/market-data/bonds-traded-in-capital-market",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1}/{max_retries}...")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            print(f"✅ Successfully fetched data from NSE")
            return data

        except requests.exceptions.Timeout:
            print(f"Timeout, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {str(e)[:100]}")
            time.sleep(retry_delay)

    print("⚠ Failed to fetch NSE bonds data after multiple retries.")
    return None


def step2_convert_to_dataframe(data):
    """Step 2: Convert JSON to DataFrame matching input.csv format"""
    print("\n" + "=" * 60)
    print("STEP 2: Converting JSON to DataFrame")
    print("=" * 60)

    if not data or "data" not in data:
        print("❌ No data found in response")
        return None

    # Extract the data array
    bonds_data = data["data"]
    print(f"\nFound {len(bonds_data)} bonds in response")

    # Extract relevant fields matching your input.csv format
    records = []
    for bond in bonds_data:
        record = {
            "SYMBOL": bond.get("symbol", ""),
            "SERIES": bond.get("series", ""),
            "ISIN": bond.get("isinCode", ""),
            "FACE VALUE": bond.get("faceValue", 100),
            "OPEN": bond.get("open", 0) if bond.get("open") != 0 else "-",
            "HIGH": bond.get("dayHigh", 0) if bond.get("dayHigh") != 0 else "-",
            "LOW": bond.get("dayLow", 0) if bond.get("dayLow") != 0 else "-",
            "LTP": bond.get("lastPrice", 0) if bond.get("lastPrice") else "-",
            "PREV.CLOSE": bond.get("previousClose", 0),
            "%CHNG": bond.get("pChange", 0),
            "VOLUME": bond.get("totalTradedVolume", 0),
            "VALUE(₹ Crores)": bond.get("totalTradedValue", 0)
            if bond.get("totalTradedValue", 0) != 0
            else "-",
        }
        records.append(record)

    df = pd.DataFrame(records)

    # Convert VALUE to crores if it's numeric
    def format_value(val):
        if val == "-" or val == 0:
            return "-"
        try:
            crores = float(val) / 10000000
            if crores < 0.01:
                return "-"
            return f"{crores:.2f}"
        except:
            return val

    df["VALUE(₹ Crores)"] = df["VALUE(₹ Crores)"].apply(format_value)

    print(f"✅ Created DataFrame with {len(df)} rows")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nFirst 3 rows:")
    print(df.head(3).to_string())

    return df


def step3_save_input_csv(df, filename="input.csv"):
    """Step 3: Save as input.csv (before maturity enrichment)"""
    print("\n" + "=" * 60)
    print(f"STEP 3: Saving as {filename}")
    print("=" * 60)

    df.to_csv(filename, index=False)
    print(f"✅ Saved {len(df)} bonds to {filename}")

    return df


def step4_add_all_columns(df):
    """Step 4: Enrich with ALL columns from NSDL (matching output.csv)"""
    print("\n" + "=" * 60)
    print("STEP 4: Adding All Columns from NSDL")
    print("=" * 60)

    # Add all columns like output.csv
    df["Maturity Date"] = ""
    df["Raw Date Code"] = ""
    df["ISIN Description"] = ""
    df["Error"] = ""

    total = len(df)
    print(f"\nProcessing {total} bonds...")

    for idx, row in df.iterrows():
        isin = str(row["ISIN"]).strip()
        symbol = str(row["SYMBOL"]).strip()

        print(f"\n[{idx + 1}/{total}] {symbol} (ISIN: {isin})")

        maturity, raw_date, description, error = fetch_isin_data(isin)

        df.at[idx, "Maturity Date"] = maturity if maturity else ""
        df.at[idx, "Raw Date Code"] = raw_date if raw_date else ""
        df.at[idx, "ISIN Description"] = description if description else ""
        df.at[idx, "Error"] = error if error else ""

        if maturity:
            print(f"  ✓ Maturity: {maturity} (from: {raw_date})")
        else:
            print(f"  ✗ Error: {error}")

        # Delay to be respectful
        time.sleep(0.5)

    print(f"\n✅ Completed data enrichment")
    return df


def extract_coupon_info(isin_desc: str) -> float | None:
    """Extract coupon rate from ISIN description"""
    if not isin_desc or not isinstance(isin_desc, str):
        return None

    desc = str(isin_desc).strip()

    # Try to find pattern like "X.XX FV" or "X.XX% FV"
    match = re.search(r"(\d+\.\d+)\s*(?:%)?.*?FV", desc)
    if match:
        return float(match.group(1)) / 100.0

    # Try to find any percentage-like number between 2-20
    numbers = re.findall(r"\b(\d+\.\d+)\b", desc)
    for num in numbers:
        rate = float(num)
        if 2.0 <= rate <= 20.0:
            return rate / 100.0

    return None


def clean_bond_name(isin_desc: str, symbol: str, isin: str) -> str:
    """Clean and format bond name from ISIN description"""
    if not isin_desc:
        return f"{symbol} ({isin})" if isin else symbol

    desc = str(isin_desc).strip()

    # Remove coupon and face value patterns
    name = re.sub(r"\d+\.\d+\s*(?:%)?.*?FV\s*RS\s*\d+", "", desc).strip()

    if not name:
        name = f"{symbol} ({isin})" if isin else symbol

    return name


def preprocess_bonds_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess bonds data using pandas (equivalent to Pathway's preprocess_bonds)
    Filters, validates, and enriches bond data.

    Returns a cleaned DataFrame with standardized columns.
    """
    print("\n" + "=" * 60)
    print("BOND DATA PREPROCESSING (Pandas)")
    print("=" * 60)

    # Step 1: Filter empty identifiers (SYMBOL or ISIN must be non-empty)
    df = df[(df["SYMBOL"] != "") | (df["ISIN"] != "")].copy()
    print(f"✓ After filtering empty identifiers: {len(df)} bonds")

    # Step 2: Parse maturity date
    df["parsed_maturity"] = df["Maturity Date"].apply(
        lambda x: pd.to_datetime(x, format="%Y-%m-%d", errors="coerce")
        if x and isinstance(x, str) and x.strip()
        else None
    )
    print(f"✓ Parsed maturity dates")

    # Step 3: Extract coupon rate
    df["coupon_rate"] = df["ISIN Description"].apply(extract_coupon_info)
    print(f"✓ Extracted coupon rates")

    # Step 4: Clean bond names
    df["clean_name"] = df.apply(
        lambda row: clean_bond_name(
            row["ISIN Description"], row["SYMBOL"], row["ISIN"]
        ),
        axis=1,
    )
    print(f"✓ Cleaned bond names")

    # Step 5: Filter rows with valid maturity dates
    df = df[df["parsed_maturity"].notna()].copy()
    print(f"✓ After filtering invalid maturity dates: {len(df)} bonds")

    # Step 6: Filter rows with valid coupon rates
    df = df[df["coupon_rate"].notna()].copy()
    print(f"✓ After filtering invalid coupon rates: {len(df)} bonds")

    # Step 7: Standardize face value
    df["face_value_clean"] = df["FACE VALUE"].apply(lambda x: x if x > 0 else 100.0)
    print(f"✓ Standardized face values")

    # Step 8: Select and rename final columns
    result = df[
        [
            "SYMBOL",
            "ISIN",
            "clean_name",
            "face_value_clean",
            "coupon_rate",
            "parsed_maturity",
            "LTP",
            "ISIN Description",
        ]
    ].copy()

    result.columns = [
        "symbol",
        "isin",
        "name",
        "face_value",
        "coupon_rate",
        "maturity_date",
        "close_price",
        "description",
    ]

    # Add coupon frequency (fixed at 2 for Indian bonds)
    result["coupon_frequency"] = 2

    # Reorder columns to match Pathway output
    result = result[
        [
            "symbol",
            "isin",
            "name",
            "face_value",
            "coupon_rate",
            "coupon_frequency",
            "maturity_date",
            "close_price",
            "description",
        ]
    ]

    print(f"\n✅ Preprocessing complete: {len(result)} bonds ready for analysis")
    print(f"Final columns: {list(result.columns)}")

    return result


def save_bond_snapshot(
    df: pd.DataFrame, filename: str = "../output_forecasts/bond_snapshot.csv"
) -> None:
    """
    Save preprocessed bond data as bond_snapshot.csv
    """
    print("\n" + "=" * 60)
    print(f"SAVING BOND SNAPSHOT: {filename}")
    print("=" * 60)

    # Ensure directory exists
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(filename, index=False)
    print(f"✅ Saved {len(df)} bonds to {filename}")
    print(f"Columns: {list(df.columns)}")


def step5_save_output_csv(df, filename="output.csv"):
    """Step 5: Save final output with ALL columns and append to historical data"""
    print("\n" + "=" * 60)
    print(f"STEP 5: Saving Final Output to {filename}")
    print("=" * 60)

    df.to_csv(filename, index=False)

    # Append data to historical_bonds_data.csv
    historical_file = HISTORICAL_BONDS_FILE
    if Path(historical_file).exists():
        # File exists, append without header
        df.to_csv(historical_file, mode="a", header=False, index=False)
        print(f"✅ Appended {len(df)} bonds to {historical_file}")
    else:
        # File doesn't exist, create it with header
        df.to_csv(historical_file, index=False)
        print(f"✅ Created new {historical_file} with {len(df)} bonds")

    # Count how many maturity dates were found
    maturity_count = df["Maturity Date"].astype(bool).sum()
    print(f"\n✅ Saved {len(df)} bonds to {filename}")
    print(
        f"📊 Maturity dates found: {maturity_count}/{len(df)} ({maturity_count / len(df) * 100:.1f}%)"
    )
    print(f"\nFinal columns: {list(df.columns)}")

    return df


# ==================== BOND PRICING FUNCTIONS (From pathway_consumer) ====================


def nelson_siegel(tau, beta0, beta1, beta2, lambda_param):
    """Nelson-Siegel yield curve model"""
    if tau <= 0:
        return beta0
    term1 = (1 - np.exp(-lambda_param * tau)) / (lambda_param * tau)
    term2 = term1 - np.exp(-lambda_param * tau)
    return beta0 + beta1 * term1 + beta2 * term2


def objective_function(params, maturities, yields, weights, alpha=0.01):
    """Objective function for yield curve fitting"""
    beta0, beta1, beta2, lambda_param = params
    predicted_yields = [
        nelson_siegel(tau, beta0, beta1, beta2, lambda_param) for tau in maturities
    ]
    errors = np.array(yields) - np.array(predicted_yields)
    weighted_mse = np.sum(weights * errors**2)
    return weighted_mse + alpha * (beta1**2 + beta2**2)


def fit_nelson_siegel_weighted(maturities, yields, target_maturity):
    """Fit Nelson-Siegel parameters with weighted optimization"""
    distances = np.abs(maturities - target_maturity)
    weights = 1 / (1 + distances)
    weights = weights / weights.sum()
    bounds = [(0, 0.20), (-0.15, 0.15), (-0.15, 0.15), (0.1, 3)]

    initial_guesses = [
        [yields[-1], yields[0] - yields[-1], 0, 0.6],
        [yields.mean(), yields[0] - yields.mean(), 0, 1.0],
    ]

    for initial_params in initial_guesses:
        try:
            result = minimize(
                objective_function,
                initial_params,
                args=(maturities, yields, weights),
                method="L-BFGS-B",
                bounds=bounds,
            )
            if result.success:
                return result.x
        except:
            continue
    return initial_guesses[0]


def ensemble_extrapolate_yield(maturities, yields, target_maturity):
    """Ensemble method for yield curve extrapolation"""
    # Linear Fallback for very short term
    if target_maturity < 0.25:
        if target_maturity <= maturities[0]:
            return yields[0]
        return yields[0]

    try:
        # Nelson-Siegel
        ns_pred = nelson_siegel(
            target_maturity,
            *fit_nelson_siegel_weighted(maturities, yields, target_maturity),
        )

        # Cubic Spline
        try:
            cs = CubicSpline(maturities, yields, bc_type="natural")
        except:
            cs = lambda x: yields[0]
        spline_pred = cs(target_maturity)

        # Linear Interpolation
        if target_maturity >= maturities[-1]:
            lin_pred = yields[-1]
        elif target_maturity <= maturities[0]:
            lin_pred = yields[0]
        else:
            lin_pred = np.interp(target_maturity, maturities, yields)

        # Weighted Ensemble
        return 0.4 * ns_pred + 0.4 * float(spline_pred) + 0.2 * lin_pred
    except Exception as e:
        return yields[0]


def generate_cash_flows(
    face_value, coupon_rate, coupon_frequency, valuation_date, maturity_date
):
    """Generate cash flows for a bond"""
    if isinstance(valuation_date, str):
        valuation_date = pd.to_datetime(valuation_date)
    if isinstance(maturity_date, str):
        maturity_date = pd.to_datetime(maturity_date)

    if valuation_date >= maturity_date:
        return []

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
        years = (p_date - valuation_date).days / 365.25
        if years <= 0:
            continue
        amount = (
            coupon_payment + face_value
            if i == len(payment_dates) - 1
            else coupon_payment
        )
        cash_flows.append({"years": years, "amount": amount})
    return cash_flows


def price_bond_dirty_price(bond, yield_curve_data, valuation_date):
    """Calculate bond price using dirty price method"""
    try:
        cash_flows = generate_cash_flows(
            bond["face_value"],
            bond["coupon_rate"],
            bond["coupon_frequency"],
            valuation_date,
            bond["maturity_date"],
        )
        if not cash_flows:
            return None

        maturities = np.array(sorted(yield_curve_data.keys()))
        yields = np.array([yield_curve_data[m] for m in maturities])

        price = 0
        for cf in cash_flows:
            rate = ensemble_extrapolate_yield(maturities, yields, cf["years"])
            price += cf["amount"] / ((1 + rate) ** cf["years"])
        return price
    except:
        return None


def run_bond_pricing():
    """Generate bond price forecasts from yield forecasts"""
    logger = logging.getLogger("BondPricing")
    logger.info("Starting bond pricing calculation...")

    if not os.path.exists(FORECAST_FILE) or not os.path.exists(BONDS_FILE):
        logger.error(
            f"Input files not found. Forecast: {os.path.exists(FORECAST_FILE)}, Bonds: {os.path.exists(BONDS_FILE)}"
        )
        return False

    try:
        # 1. Load Forecasts
        forecast_df = pd.read_csv(FORECAST_FILE)
        forecast_df["Forecast_Generation_Date"] = pd.to_datetime(
            forecast_df["Forecast_Generation_Date"]
        )
        latest_gen_date = forecast_df["Forecast_Generation_Date"].max()
        logger.info(f"Using forecasts generated on: {latest_gen_date}")

        # Filter for latest run and diff == 1
        forecast_df = forecast_df[
            (forecast_df["Forecast_Generation_Date"] == latest_gen_date)
            & (forecast_df["diff"] == 1)
        ]
        forecast_df["Target_Date"] = pd.to_datetime(
            forecast_df["Target_Date"]
        ).dt.strftime("%Y-%m-%d")
        logger.info(f"Filtered to {len(forecast_df)} forecasts with diff=1")
    except Exception as e:
        logger.error(f"Error reading forecasts: {e}")
        return False

    try:
        # 2. Load Bonds
        bonds_df = pd.read_csv(BONDS_FILE)
        bonds_list = bonds_df.to_dict("records")
        logger.info(f"Loaded {len(bonds_list)} bonds for pricing.")
    except Exception as e:
        logger.error(f"Error reading bonds: {e}")
        return False

    try:
        # 3. Compute Prices
        logger.info("Calculating future bond prices...")
        unique_dates = sorted(forecast_df["Target_Date"].unique())
        results = []

        for date_str in unique_dates:
            # Build yield curve for this specific day
            day_data = forecast_df[forecast_df["Target_Date"] == date_str]
            curve = {
                row["Maturity"]: row["Predicted_Yield"] / 100.0
                for _, row in day_data.iterrows()
            }

            if len(curve) < 2:
                continue

            for bond in bonds_list:
                price = price_bond_dirty_price(bond, curve, date_str)
                if price:
                    results.append(
                        {
                            "Date": date_str,
                            "Bond_Name": bond["name"],
                            "Predicted_Price": price,
                            "Maturity_Date": bond["maturity_date"],
                            "Coupon": bond["coupon_rate"],
                        }
                    )

        # 4. Generate Summary Report
        if results:
            res_df = pd.DataFrame(results)
            res_df["Date"] = pd.to_datetime(res_df["Date"])
            # Sort by Date and Bond Name
            res_df = res_df.sort_values(["Date", "Bond_Name"])

            # Save to disk
            output_csv = os.path.join(OUTPUT_DIR, "bond_price_report.csv")
            res_df.to_csv(output_csv, index=False)

            logger.info("\n" + "=" * 80)
            logger.info("BOND PRICING SUMMARY REPORT")
            logger.info("=" * 80)

            for bond_name in res_df["Bond_Name"].unique():
                subset = res_df[res_df["Bond_Name"] == bond_name]
                start_price = subset.iloc[0]["Predicted_Price"]
                end_price = subset.iloc[-1]["Predicted_Price"]
                change = end_price - start_price
                pct = (change / start_price) * 100

                logger.info(
                    f"{bond_name[:40]:<40} | Start: ${start_price:6.2f} | End: ${end_price:6.2f} | Chg: {pct:+5.2f}%"
                )

            logger.info("=" * 80)
            logger.info(f"Detailed report saved to: {output_csv}")
            return True
        else:
            logger.warning("No prices could be calculated.")
            return False
    except Exception as e:
        logger.error(f"Error during pricing: {e}", exc_info=True)
        return False


def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("NSE BONDS DATA FETCHER WITH ALL COLUMNS")
    print("=" * 60)

    # Step 1: Fetch from NSE
    data = step1_fetch_nse_bonds()
    if not data:
        return

    # Step 2: Convert to DataFrame
    df = step2_convert_to_dataframe(data)
    if df is None:
        return

    # # Step 3: Save input.csv
    # df = step3_save_input_csv(df, 'input.csv')

    # Step 4: Add ALL columns (Maturity Date, Raw Date Code, ISIN Description, Error)
    df = step4_add_all_columns(df)

    # Step 5: Save output.csv
    df = step5_save_output_csv(df, "../output_forecasts/bonds_data.csv")

    # NEW: Preprocess bonds and create bond_snapshot.csv
    preprocessed_df = preprocess_bonds_pandas(df)
    save_bond_snapshot(preprocessed_df, "../output_forecasts/bond_snapshot.csv")

    print("\n" + "=" * 60)
    print("✅ ALL SCRAPER STEPS COMPLETED SUCCESSFULLY! NOW PRICING")
    print("=" * 60)


def run_full_pipeline():
    """Run the complete pipeline: fetch bonds, preprocess, and price"""
    logger = logging.getLogger("Pipeline")

    print("\n" + "=" * 80)
    print(
        f"STARTING FULL PIPELINE EXECUTION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 80)

    try:
        # Run the main NSE fetching and preprocessing
        main()

        # Run bond pricing
        pricing_success = run_bond_pricing()

        if pricing_success:
            logger.info(f"✅ Pipeline completed successfully at {datetime.now()}")
        else:
            logger.warning(
                f"⚠️ Pipeline completed with pricing warnings at {datetime.now()}"
            )

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)


def schedule_pipeline():
    """Schedule the pipeline to run every 24 hours"""
    logger = logging.getLogger("Scheduler")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("pipeline_scheduler.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info("=" * 80)
    logger.info("NSE GSEC BOND ANALYSIS PIPELINE - SCHEDULER STARTED")
    logger.info("=" * 80)
    logger.info(f"Pipeline will run every 24 hours starting from {datetime.now()}")

    # Schedule the pipeline to run every 24 hours
    schedule.every(24).hours.do(run_full_pipeline)

    # Run indefinitely
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute if a task needs to be run
    except KeyboardInterrupt:
        logger.info("\n✅ Scheduler stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import sys

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        # Run in scheduler mode (24 hour interval)
        run_full_pipeline()
        schedule_pipeline()
    else:
        # Run once
        run_full_pipeline()
