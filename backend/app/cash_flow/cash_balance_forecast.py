import pandas as pd
import joblib
import os
import glob
import numpy as np
from scipy.interpolate import CubicSpline


def forecast_next_30_days(models_dir, data_dir, raw_data_file):
    """
    Loads raw bank balance data, runs ML models for 1/3/5/7/14/30 day windows,
    fits a spline curve on the 6 predictions, and generates 30 daily closing balance forecasts.

    Returns:
        list of 30 predicted balances (day 1 -> day 30)
    """

    # ----- Load raw data to get the latest closing balance -----
    df = pd.read_csv(raw_data_file)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    last_closing_balance = df["closing_cash_balance"].iloc[-1]

    # ----- Supported windows -----
    horizons = [1, 3, 5, 7, 14, 30]
    predictions = {}

    # ----- Get prediction for every horizon -----
    for window_size in horizons:
        model_pattern = f"*_H{window_size}_F{window_size}.pkl"
        model_files = glob.glob(os.path.join(models_dir, model_pattern))
        if not model_files:
            raise FileNotFoundError(f"No model found for window size {window_size}")

        model = joblib.load(model_files[0])

        dataset_file = os.path.join(
            data_dir, f"dataset_H{window_size}_F{window_size}.csv"
        )
        if not os.path.exists(dataset_file):
            raise FileNotFoundError(f"Dataset file missing: {dataset_file}")

        df_ds = pd.read_csv(dataset_file)
        last_row = df_ds.iloc[-1:].copy()

        target_col = "target_next_window_cashflow"
        X_pred = last_row.drop(columns=[target_col], errors="ignore").fillna(0)

        if hasattr(model, "feature_names_in_"):
            X_pred = X_pred[model.feature_names_in_]

        pred_cashflow = model.predict(X_pred)[0]
        closing_balance_future = last_closing_balance + pred_cashflow
        predictions[window_size] = closing_balance_future

    # ----- Fit spline curve on 6 datapoints -----
    X = np.array(horizons)  # [1,3,5,7,14,30]
    Y = np.array([predictions[h] for h in horizons])

    spline = CubicSpline(X, Y)
    days = np.arange(1, 31)  # 1 → 30 days
    interpolated_30 = spline(days).tolist()

    return interpolated_30
