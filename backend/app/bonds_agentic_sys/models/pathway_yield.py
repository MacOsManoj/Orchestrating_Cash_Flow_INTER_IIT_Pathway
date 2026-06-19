import pathway as pw
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import os
import csv
import time

# ==================== CONFIGURATION ====================
FORECAST_DAYS = 14
LOOKBACK_DAYS = 365

INPUT_FILES = {1: "1y.csv", 2: "2y.csv", 5: "5y.csv", 7: "7y.csv", 10: "10y.csv"}

OUTPUT_DIR = "output_forecasts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==================== SCHEMA ====================
class YieldSchema(pw.Schema):
    """Schema for yield curve data"""

    date: str
    open: float
    high: float
    low: float
    close: float
    maturity: int


# ==================== STREAMING SUBJECT ====================
class YieldStreamSubject(pw.io.python.ConnectorSubject):
    """Stream yield data from CSV files"""

    def __init__(self, maturity: int, csv_path: str, delay_seconds: float = 0.001):
        super().__init__()
        self.maturity = maturity
        self.csv_path = csv_path
        self.delay_seconds = delay_seconds

    def run(self):
        """Read CSV row by row and emit as streaming data"""
        with open(self.csv_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    date_str = row.get("Date", "").strip()
                    # Standardize Date Format
                    try:
                        dt = datetime.strptime(date_str, "%m/%d/%Y")
                    except ValueError:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")

                    def clean_value(val):
                        if isinstance(val, str):
                            cleaned = val.replace("%", "").strip()
                            return float(cleaned) if cleaned else 0.0
                        return float(val)

                    data = {
                        "date": dt.isoformat(),
                        "open": clean_value(row.get("Open", "0.0")),
                        "high": clean_value(row.get("High", "0.0")),
                        "low": clean_value(row.get("Low", "0.0")),
                        "close": clean_value(row.get("Close", "0.0")),
                        "maturity": self.maturity,
                    }

                    self.next(**data)
                    # Tiny sleep to simulate stream, but fast enough for batch
                    time.sleep(self.delay_seconds)
                except Exception as e:
                    continue


# ==================== TRAINING DATA ACCUMULATOR ====================
class TrainingDataAccumulator(pw.BaseCustomAccumulator):
    """
    Accumulates last 365 days of data.
    """

    def __init__(self, records):
        self.records = deque(records, maxlen=LOOKBACK_DAYS)

    @classmethod
    def from_row(cls, row):
        return cls([tuple(row)])

    def update(self, other):
        self.records.extend(other.records)

    def retract(self, other):
        for rec in other.records:
            try:
                self.records.remove(rec)
            except ValueError:
                pass

    def compute_result(self):
        if len(self.records) < 3:
            return {"ready": False}

        # Sort by date to ensure order
        sorted_records = sorted(self.records, key=lambda x: x[0])

        dates = [r[0] for r in sorted_records]
        opens = [r[1] for r in sorted_records]
        highs = [r[2] for r in sorted_records]
        lows = [r[3] for r in sorted_records]
        closes = [r[4] for r in sorted_records]

        # Calculate returns
        returns = []
        for i in range(1, len(closes)):
            ret = (
                (closes[i] - closes[i - 1]) / closes[i - 1]
                if closes[i - 1] != 0
                else 0.0
            )
            returns.append(ret)

        bodies = [closes[i] - opens[i] for i in range(len(closes))]
        ranges = [highs[i] - lows[i] for i in range(len(closes))]

        # Create training samples (Day T features -> Day T+1 Close)
        training_samples = []
        for i in range(2, len(closes) - 1):
            lag_1 = returns[i - 1] if i - 1 < len(returns) else 0.0
            lag_2 = returns[i - 2] if i - 2 < len(returns) else 0.0

            # 14-day averages
            avg_body = sum(bodies[max(0, i - 13) : i + 1]) / len(
                bodies[max(0, i - 13) : i + 1]
            )
            avg_range = sum(ranges[max(0, i - 13) : i + 1]) / len(
                ranges[max(0, i - 13) : i + 1]
            )

            training_samples.append(
                {
                    "lag_1_return": lag_1,
                    "lag_2_return": lag_2,
                    "body": bodies[i],
                    "range": ranges[i],
                    "avg_body_14": avg_body,
                    "avg_range_14": avg_range,
                    "current_close": closes[i],
                    "target": closes[i + 1],  # Next day's close
                }
            )

        # Latest features for the Forecast Step
        current_return = returns[-1] if returns else 0.0
        lag_1_return = returns[-2] if len(returns) >= 2 else 0.0

        return {
            "ready": len(training_samples) >= 30,
            "training_samples": training_samples,
            "last_date": dates[-1],  # This is the "Current Date" of the stream
            "last_close": closes[-1],
            "last_return": current_return,
            "last_lag_1_return": lag_1_return,
            "last_avg_body_14": sum(bodies[-14:]) / len(bodies[-14:])
            if len(bodies) >= 14
            else sum(bodies) / len(bodies),
            "last_avg_range_14": sum(ranges[-14:]) / len(ranges[-14:])
            if len(ranges) >= 14
            else sum(ranges) / len(ranges),
        }


# ==================== MODEL TRAINER ====================
class ElasticNetTrainer(pw.BaseCustomAccumulator):
    def __init__(self, data_dict):
        # Handle Pathway object wrapping
        if hasattr(data_dict, "as_dict"):
            self.data_dict = data_dict.as_dict()
        elif isinstance(data_dict, dict):
            self.data_dict = data_dict
        else:
            self.data_dict = {}

    @classmethod
    def from_row(cls, row):
        return cls(row[0])

    def update(self, other):
        if other.data_dict.get("ready", False):
            self.data_dict = other.data_dict

    def retract(self, other):
        pass

    def compute_result(self):
        data_dict = self.data_dict
        if hasattr(data_dict, "as_dict"):
            data_dict = data_dict.as_dict()

        training_samples = data_dict.get("training_samples", [])

        if not data_dict.get("ready", False) or len(training_samples) < 10:
            return {"trained": False}

        # Prepare Matrix
        X = np.array(
            [
                [
                    s["lag_1_return"],
                    s["lag_2_return"],
                    s["body"],
                    s["range"],
                    s["avg_body_14"],
                    s["avg_range_14"],
                    s["current_close"],
                ]
                for s in training_samples
            ]
        )
        y = np.array([s["target"] for s in training_samples])

        # Simple Standardization
        mean = X.mean(axis=0)
        std = X.std(axis=0) + 1e-8
        X_scaled = (X - mean) / std

        # Coordinate Descent (ElasticNet)
        n_features = X_scaled.shape[1]
        weights = np.zeros(n_features)
        intercept = y.mean()
        alpha = 0.001
        l1_ratio = 0.5

        # Quick training loop
        for _ in range(50):
            for j in range(n_features):
                residual = (
                    y - intercept - (X_scaled @ weights) + (X_scaled[:, j] * weights[j])
                )
                rho = (X_scaled[:, j] * residual).sum()
                z = (X_scaled[:, j] ** 2).sum() + alpha * (1 - l1_ratio) * len(y)
                threshold = alpha * l1_ratio * len(y)

                if rho < -threshold:
                    weights[j] = (rho + threshold) / z
                elif rho > threshold:
                    weights[j] = (rho - threshold) / z
                else:
                    weights[j] = 0.0
            intercept = (y - (X_scaled @ weights)).mean()

        return {
            "trained": True,
            "weights": weights.tolist(),
            "intercept": float(intercept),
            "mean": mean.tolist(),
            "std": std.tolist(),
            # Pass through last features so Forecaster doesn't need to look up
            "last_features": {
                "last_date": data_dict.get("last_date"),
                "last_close": data_dict.get("last_close"),
                "last_return": data_dict.get("last_return"),
                "last_lag_1_return": data_dict.get("last_lag_1_return"),
                "last_avg_body_14": data_dict.get("last_avg_body_14"),
                "last_avg_range_14": data_dict.get("last_avg_range_14"),
            },
        }


training_reducer = pw.reducers.udf_reducer(TrainingDataAccumulator)
model_reducer = pw.reducers.udf_reducer(ElasticNetTrainer)


# ==================== FORECASTING LOGIC ====================
@pw.udf(deterministic=True)
def generate_forecast(model_dict, maturity):
    if hasattr(model_dict, "as_dict"):
        model_dict = model_dict.as_dict()

    if not model_dict.get("trained", False):
        return {"forecasts": []}

    # Unpack Model
    weights = np.array(model_dict["weights"])
    intercept = model_dict["intercept"]
    mean = np.array(model_dict["mean"])
    std = np.array(model_dict["std"])
    last = model_dict["last_features"]

    # Init Recursion
    curr_close = last["last_close"]
    lag_1 = last["last_return"]
    lag_2 = last["last_lag_1_return"]
    avg_body = last["last_avg_body_14"]
    avg_range = last["last_avg_range_14"]

    try:
        start_date = datetime.fromisoformat(last["last_date"])
    except:
        return {"forecasts": []}

    # --- CORRECTED LOOP STRUCTURE START ---
    results = []
    current_date = start_date  # Initialize ONCE before the loop

    for i in range(FORECAST_DAYS):
        # 1. Construct Feature Vector
        feats = np.array(
            [lag_1, lag_2, avg_body, avg_range, avg_body, avg_range, curr_close]
        )
        feats_scaled = (feats - mean) / std

        # 2. Predict
        pred_close = intercept + (feats_scaled @ weights)
        pred_return = (pred_close - curr_close) / curr_close if curr_close else 0

        # 3. Advance Date (Iterative Business Day Logic)
        # Adds 1 day, then keeps adding if it lands on Sat/Sun
        current_date += timedelta(days=1)
        while current_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            current_date += timedelta(days=1)

        results.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "predicted_close": float(pred_close),
                "predicted_return": float(pred_return),
            }
        )

        # 4. Recursion Updates (Prepare for next iteration)
        lag_2 = lag_1
        lag_1 = pred_return
        curr_close = pred_close
    # --- CORRECTED LOOP STRUCTURE END ---

    return {"maturity": maturity, "forecasts": results}


# ==================== EXTRACTION UDFs (Unchanged) ====================
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


# ==================== MAIN PIPELINE ====================
def build_pipeline(maturity, csv_path, target_date_obj):
    # 1. Ingest
    stream = pw.io.python.read(
        YieldStreamSubject(maturity, csv_path), schema=YieldSchema
    ).select(
        date=pw.this.date.dt.strptime("%Y-%m-%dT%H:%M:%S"),
        open=pw.this.open,
        high=pw.this.high,
        low=pw.this.low,
        close=pw.this.close,
        maturity=pw.this.maturity,
    )

    # 2. Accumulate History
    history = stream.windowby(
        stream.date,
        window=pw.temporal.sliding(
            duration=timedelta(days=LOOKBACK_DAYS), hop=timedelta(days=1)
        ),
        instance=stream.maturity,
        behavior=pw.temporal.exactly_once_behavior(),
    ).reduce(
        maturity=pw.this._pw_instance,
        date=pw.reducers.max(pw.this.date),
        data_dict=training_reducer(
            pw.this.date, pw.this.open, pw.this.high, pw.this.low, pw.this.close
        ),
    )

    # 3. Train Model
    models = history.windowby(
        history.date,
        window=pw.temporal.tumbling(duration=timedelta(days=1)),
        instance=history.maturity,
        behavior=pw.temporal.exactly_once_behavior(),
    ).reduce(
        maturity=pw.this._pw_instance,
        date=pw.reducers.max(pw.this.date),
        model=model_reducer(pw.this.data_dict),
    )

    # 4. FILTER: Only keep the model trained on the LAST date
    # This prevents forecasting for every historical day
    final_model = models.filter(pw.this.date == target_date_obj)

    # 5. Forecast (Only runs once because of the filter)
    result = final_model.select(
        maturity=pw.this.maturity,
        forecast_date=pw.this.date,
        forecast_data=generate_forecast(pw.this.model, pw.this.maturity),
    )

    return result


if __name__ == "__main__":
    tables = []

    print("Initializing...")

    for mat, fname in INPUT_FILES.items():
        if os.path.exists(fname):
            # A. Pre-scan file to find the Last Date
            df = pd.read_csv(fname)
            # Ensure correct format matching the Pathway stream
            try:
                # Assuming MM/DD/YYYY in CSV
                last_ts = pd.to_datetime(df["Date"], dayfirst=False).max()
            except:
                # Fallback for DD/MM/YYYY
                last_ts = pd.to_datetime(df["Date"], dayfirst=True).max()

            print(f"Maturity {mat}Y: Last Date is {last_ts.date()}")

            # B. Build Pipeline with Filter
            tbl = build_pipeline(mat, fname, last_ts)
            tables.append(tbl)

    if tables:
        # Combine all maturities
        combined = tables[0]
        for t in tables[1:]:
            combined = combined.concat_reindex(t)

        # Extract rows for CSV
        output_rows = []
        for d in range(FORECAST_DAYS):
            row = combined.select(
                Maturity=get_maturity(pw.this.forecast_data),
                Forecast_Generation_Date=pw.this.forecast_date,
                Prediction_Day=d + 1,
                Target_Date=get_forecast_day(pw.this.forecast_data, d),
                Predicted_Yield=get_predicted_close(pw.this.forecast_data, d),
                Predicted_Return=get_predicted_return(pw.this.forecast_data, d),
            )
            output_rows.append(row)

        # Merge all days
        final_output = output_rows[0]
        for r in output_rows[1:]:
            final_output = final_output.concat_reindex(r)

        # Write Result
        outfile = f"{OUTPUT_DIR}/final_forecasts.csv"
        pw.io.csv.write(final_output, outfile)

        print(f"Running pipeline. Forecasts will appear in: {outfile}")
        pw.run()
    else:
        print("No files found.")
