import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy.interpolate import CubicSpline
from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt

"""
BOND PRICING - MULTI-BOND FORECAST (PATHWAY INTEGRATED)
=======================================================
Calculates dirty bond prices for FUTURE dates for MULTIPLE bonds.
Reads yield forecasts from the single 'final_forecasts.csv' file.
"""

# ==================== NELSON-SIEGEL FUNCTIONS (Unchanged) ====================


def nelson_siegel(tau, beta0, beta1, beta2, lambda_param):
    """Calculate yield for a given maturity using Nelson-Siegel model"""
    if tau <= 0:
        return beta0
    term1 = (1 - np.exp(-lambda_param * tau)) / (lambda_param * tau)
    term2 = term1 - np.exp(-lambda_param * tau)
    return beta0 + beta1 * term1 + beta2 * term2


def objective_function(params, maturities, yields, weights, alpha=0.01):
    beta0, beta1, beta2, lambda_param = params
    predicted_yields = [
        nelson_siegel(tau, beta0, beta1, beta2, lambda_param) for tau in maturities
    ]
    errors = np.array(yields) - np.array(predicted_yields)
    weighted_mse = np.sum(weights * errors**2)
    regularization = alpha * (beta1**2 + beta2**2)
    return weighted_mse + regularization


def fit_nelson_siegel_weighted(maturities, yields, target_maturity):
    distances = np.abs(maturities - target_maturity)
    weights = 1 / (1 + distances)
    weights = weights / weights.sum()

    # Bounds tailored for decimal yields (0.05 = 5%)
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
            if result.fun < best_error:
                best_error = result.fun
                best_result = result
        except:
            continue

    return best_result.x if best_result else initial_guesses[0]


def linear_interpolation(maturities, yields, target_maturity):
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
    try:
        cs = CubicSpline(maturities, yields, bc_type="natural")
        return cs(target_maturity)
    except:
        return linear_interpolation(maturities, yields, target_maturity)


def ensemble_extrapolate_yield(maturities, yields, target_maturity):
    if target_maturity < 0.25:
        return linear_interpolation(maturities, yields, target_maturity)

    ns_params = fit_nelson_siegel_weighted(maturities, yields, target_maturity)
    ns_pred = nelson_siegel(target_maturity, *ns_params)
    spline_pred = cubic_spline_interpolation(maturities, yields, target_maturity)
    linear_pred = linear_interpolation(maturities, yields, target_maturity)

    weights = [0.4, 0.4, 0.2]
    ensemble_pred = (
        weights[0] * ns_pred + weights[1] * spline_pred + weights[2] * linear_pred
    )

    return ensemble_pred


# ==================== BOND PRICING CORE (Unchanged) ====================


def calculate_years_to_maturity(valuation_date, maturity_date):
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
    face_value = bond_info["face_value"]
    coupon_rate = bond_info["coupon_rate"]
    coupon_frequency = bond_info["coupon_frequency"]
    maturity_date = bond_info["maturity_date"]

    cash_flows = generate_cash_flows(
        face_value, coupon_rate, coupon_frequency, valuation_date, maturity_date
    )

    if not cash_flows:
        return None

    maturities = np.array(sorted(yield_curve_data.keys()))
    yields = np.array([yield_curve_data[m] for m in maturities])

    dirty_price = 0
    for cf in cash_flows:
        discount_rate = ensemble_extrapolate_yield(maturities, yields, cf["years"])
        # Standard discount formula
        dirty_price += cf["cash_flow"] / ((1 + discount_rate) ** cf["years"])

    return dirty_price


def normalize_date(date_str):
    try:
        return pd.to_datetime(date_str).strftime("%Y-%m-%d")
    except:
        return None


# ==================== MAIN: MULTI-BOND FORECAST LOGIC (UPDATED) ====================


def price_multiple_bonds_forecast(
    bonds_list,
    forecast_file="final_forecasts.csv",
    output_file="multi_bond_forecast.csv",
):
    """
    Forecasts prices for a LIST of bonds using a single consolidated forecast file.
    """
    print(f"\n{'=' * 80}")
    print(f"MULTI-BOND PRICE FORECASTING")
    print(f"{'=' * 80}")
    print(f"Number of bonds to price: {len(bonds_list)}")

    # 1. Load Single Forecast File
    print(f"Loading yield forecasts from {forecast_file}...")
    try:
        df = pd.read_csv(forecast_file)
        # Ensure date format
        df["Target_Date"] = pd.to_datetime(df["Target_Date"]).dt.strftime("%Y-%m-%d")
    except FileNotFoundError:
        print(
            f"Error: {forecast_file} not found. Please ensure the pipeline ran successfully."
        )
        return

    # 2. Group by Date to Build Curves
    # We need a dictionary like: { '2025-11-05': {1: 0.056, 10: 0.065, ...}, ... }
    unique_dates = sorted(df["Target_Date"].unique())

    if not unique_dates:
        print("\nError: No forecast dates found in file.")
        return

    print(f"\nFound {len(unique_dates)} forecast days.")
    print(f"Period: {unique_dates[0]} to {unique_dates[-1]}")

    # 3. Price Loop (Dates -> Bonds)
    print("\nCalculating prices...")
    results = []

    for date_str in unique_dates:
        # Extract rows for this specific day
        day_data = df[df["Target_Date"] == date_str]

        # Build yield curve for this day
        # Format: { Maturity_Year: Yield_Decimal }
        curve_today = {}
        for _, row in day_data.iterrows():
            mat = float(row["Maturity"])
            yld = float(row["Predicted_Yield"])
            # CRITICAL: Convert percentage (5.64) to decimal (0.0564)
            curve_today[mat] = yld / 100.0

        # Ensure we have enough points to interpolate
        if len(curve_today) < 2:
            print(
                f"  Skipping {date_str}: Not enough yield points (Found {len(curve_today)})"
            )
            continue

        # Iterate through every bond in the list
        for bond in bonds_list:
            price = price_bond_dirty_price(bond, curve_today, date_str)

            if price is not None:
                results.append(
                    {
                        "Date": date_str,
                        "Bond_Name": bond.get("name", "Unknown Bond"),
                        "Predicted_Price": price,
                        "Maturity_Date": bond["maturity_date"],
                        "Coupon": bond["coupon_rate"],
                    }
                )

    # 4. Save Results
    if not results:
        print("No prices calculated. Check your dates and bond maturities.")
        return

    results_df = pd.DataFrame(results)
    results_df["Date"] = pd.to_datetime(results_df["Date"])
    results_df = results_df.sort_values(["Date", "Bond_Name"])

    results_df.to_csv(output_file, index=False)
    print(f"\n Forecast saved to: {output_file}")

    # 5. Plotting (Multiple Lines)
    plt.figure(figsize=(12, 7))

    # Group by bond name to plot separate lines
    for name, group in results_df.groupby("Bond_Name"):
        plt.plot(
            group["Date"],
            group["Predicted_Price"],
            marker="o",
            linestyle="-",
            linewidth=2,
            label=name,
            markersize=4,
        )

        # Annotate last price
        last_date = group["Date"].iloc[-1]
        last_price = group["Predicted_Price"].iloc[-1]
        plt.annotate(
            f"{last_price:.2f}",
            (last_date, last_price),
            textcoords="offset points",
            xytext=(10, 0),
            va="center",
        )

    plt.title(
        f"Forecasted Bond Prices: Next {len(unique_dates)} Trading Days",
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Dirty Price ($)", fontsize=12)
    plt.grid(True, alpha=0.3, linestyle="--")
    plt.legend(title="Bond Name")
    plt.xticks(rotation=45)

    plt.tight_layout()
    plot_file = output_file.replace(".csv", ".png")
    plt.savefig(plot_file)
    print(f" Plot saved to: {plot_file}")
    plt.show()


# ==================== USER INPUT SECTION ====================

if __name__ == "__main__":
    # 1. DEFINE YOUR FORECAST FILE
    forecast_csv = "final_forecasts.csv"

    # 2. DEFINE YOUR LIST OF BONDS HERE
    # Add as many dictionaries as you want
    my_bonds_list = [
        {
            "name": "GS 2028 (High Coupon)",
            "face_value": 100,
            "coupon_rate": 0.0706,
            "coupon_frequency": 2,
            "maturity_date": "2028-04-10",
        },
        {
            "name": "GS 2032 (Long Term)",
            "face_value": 100,
            "coupon_rate": 0.0650,
            "coupon_frequency": 2,
            "maturity_date": "2032-01-15",
        },
        {
            "name": "Short Term 2026",
            "face_value": 100,
            "coupon_rate": 0.0580,
            "coupon_frequency": 2,
            "maturity_date": "2026-05-20",
        },
    ]

    # 3. RUN THE FORECASTER
    price_multiple_bonds_forecast(my_bonds_list, forecast_csv)
