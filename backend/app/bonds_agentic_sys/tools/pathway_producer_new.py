import pathway as pw
import os
import csv
import time
import json
import re
import sys
import threading
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from river import compose, optim, tree, linear_model, preprocessing
from pathway import JoinMode
import pandas as pd
from pathway.io.csv import CsvParserSettings
import ssl
from dotenv import load_dotenv

# ==================== LOGGING CONFIGURATION ====================
"""load_dotenv('news/.env')"""


def setup_logging(log_dir="logs", log_level=logging.DEBUG):
    os.makedirs(log_dir, exist_ok=True)
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "bond_producer.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger("BondProducer")


logger = setup_logging()

# ==================== CONFIGURATION ====================

try:
    pw.set_license_key("1EBCE3-0E3417-3066F3-5C3F8A-48F543-V3")
except Exception as e:
    logger.error(f"Failed to set Pathway license key: {e}")
    raise

FORECAST_DAYS = 21
LOOKBACK_DAYS = 365

INPUT_FILES = {1: "1y.csv", 2: "2y.csv", 5: "5y.csv", 7: "7y.csv", 10: "10y.csv"}

OUTPUT_DIR = "output_forecasts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_FILE = "bonds_data.csv"
"""KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')
KAFKA_SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", None)
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME", None)
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD", None)
# KAFKA_TOPIC_RAW_NEWS = 'raw-news-feed'
# KAFKA_TOPIC_ENRICHED_NEWS = 'enriched-news'
KAFKA_TOPIC_RAW_YIELDS="raw_yield_data"""
# KAFKA_TOPIC_BONDS = "bonds_market_data"    # For Bond definitions
# KAFKA_TOPIC_YIELDS = "yield_curve_updates" # For Yield updates (1y, 2y, etc)
# KAFKA_GROUP_ID = "bonds_processor_v1"


# =============================================================================
# 1. SCHEMA DEFINITION & UDFs
# =============================================================================
class BondSchema(pw.Schema):
    SYMBOL: str
    ISIN: str
    ISIN_Description: str = pw.column_definition(name="ISIN Description")
    Maturity_Date: str = pw.column_definition(name="Maturity Date")
    FACE_VALUE: float = pw.column_definition(name="FACE VALUE", default_value=100.0)
    LTP: float


# 2. Schema for Kafka JSON Data (Clean types)
class KafkaYieldSchema(pw.Schema):
    date: str
    open: float
    high: float
    low: float
    close: float
    maturity: int


class RawYieldSchema(pw.Schema):
    Date: str
    Open: str
    High: str
    Low: str
    Close: str


class YieldSchema(pw.Schema):
    date: str
    open: float
    high: float
    low: float
    close: float
    maturity: int


"""# Build rdkafka config for Pathway
def get_rdkafka_settings() -> dict:
#Get rdkafka settings for Pathway Kafka connector.
    settings = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "pathway-pipeline",
    }
    
    if KAFKA_SECURITY_PROTOCOL == "SASL_SSL":
        settings.update({
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "PLAIN",
            "sasl.username": KAFKA_SASL_USERNAME,
            "sasl.password": KAFKA_SASL_PASSWORD,
        })
    return settings"""


@pw.udf
def parse_maturity_date(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return None


@pw.udf
def extract_coupon_info(isin_desc: str) -> float | None:
    if not isin_desc:
        return None
    desc = str(isin_desc).strip()
    match = re.search(r"(\d+\.\d+)\s*FV", desc)
    if match:
        return float(match.group(1)) / 100.0
    numbers = re.findall(r"\b(\d+\.\d+)\b", desc)
    for num in numbers:
        rate = float(num)
        if 2.0 <= rate <= 20.0:
            return rate / 100.0
    return None


@pw.udf
def clean_bond_name(isin_desc: str, symbol: str, isin: str) -> str:
    desc = str(isin_desc) if isin_desc else ""
    name = re.sub(r"\d+\.\d+\s*FV\s*RS\s*\d+", "", desc).strip()
    if not name:
        name = f"{symbol} ({isin})" if isin else symbol
    return name


def preprocess_bonds(table: pw.Table) -> pw.Table:
    table = table.filter((table.SYMBOL != "") | (table.ISIN != ""))
    table = table.with_columns(
        parsed_maturity=pw.if_else(
            table["Maturity Date"] != "",
            table["Maturity Date"].dt.strptime(fmt="%Y-%m-%d"),
            None,
        ),
        coupon_rate=extract_coupon_info(table["ISIN Description"]),
        clean_name=clean_bond_name(table["ISIN Description"], table.SYMBOL, table.ISIN),
    )
    table = table.filter(pw.this.parsed_maturity.is_not_none())
    table = table.filter(pw.this.coupon_rate.is_not_none())
    table = table.with_columns(
        face_value_clean=pw.apply(lambda x: x if x > 0 else 100.0, table["FACE VALUE"])
    )
    return table.select(
        symbol=table.SYMBOL,
        isin=table.ISIN,
        name=table.clean_name,
        face_value=table.face_value_clean,
        coupon_rate=table.coupon_rate,
        coupon_frequency=2,
        maturity_date=table.parsed_maturity,
        close_price=table.LTP,
        description=table["ISIN Description"],
    )


# ==================== YIELD PROCESSING & ML ACCUMULATORS ====================


class YieldStreamSubject(pw.io.python.ConnectorSubject):
    def __init__(self, maturity: int, csv_path: str, delay_seconds: float = 0.001):
        super().__init__()
        self.maturity = maturity
        self.csv_path = csv_path
        self.delay_seconds = delay_seconds

    def run(self):
        if not os.path.exists(self.csv_path):
            return
        with open(self.csv_path, "r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            last_dt = None
            for row in reader:
                try:
                    date_str = row.get("Date", "") or row.get("date", "")
                    try:
                        dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
                    except:
                        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
                    last_dt = dt

                    def clean(val):
                        return (
                            float(val.replace("%", "").strip() or 0)
                            if isinstance(val, str)
                            else float(val)
                        )

                    self.next(
                        date=dt.isoformat(),
                        open=clean(row.get("Open", "0")),
                        high=clean(row.get("High", "0")),
                        low=clean(row.get("Low", "0")),
                        close=clean(row.get("Close", "0")),
                        maturity=self.maturity,
                    )
                    time.sleep(self.delay_seconds)
                except:
                    continue
            if last_dt:
                # Flush
                self.next(
                    date=(last_dt + timedelta(days=1)).isoformat(),
                    open=0.0,
                    high=0.0,
                    low=0.0,
                    close=0.0,
                    maturity=self.maturity,
                )


# class RiverModelTrainer(pw.BaseCustomAccumulator):
#     def __init__(self, data_dict): self.data_dict = data_dict
#     @classmethod
#     def from_row(cls, row): return cls(row[0])
#     def update(self, other): self.data_dict = other.data_dict
#     def retract(self, other): pass
#     def compute_result(self):
#         data_dict = self.data_dict
#         if hasattr(data_dict, 'as_dict'): data_dict = data_dict.as_dict()
#         training_samples = data_dict.get('training_samples', [])
#         if not data_dict.get('ready', False) or len(training_samples) < 10: return {'trained': False}

#         model = compose.Pipeline(preprocessing.StandardScaler(), linear_model.LinearRegression(optimizer=optim.SGD(0.01), l2=0.001))
#         for sample in training_samples:
#             x = {k: sample[k] for k in ['lag_1_return', 'lag_2_return', 'body', 'range', 'avg_body_14', 'avg_range_14', 'current_close']}
#             model.learn_one(x, sample['target'])


#         lr_model = model['LinearRegression']
#         scaler = model['StandardScaler']
#         return {
#             'trained': True, 'weights': dict(lr_model.weights), 'intercept': float(lr_model.intercept),
#             'scaler_means': dict(scaler.means), 'scaler_vars': dict(scaler.vars),
#             'last_features': data_dict.get('last_features', {})
#         }
# model_reducer = pw.reducers.udf_reducer(RiverModelTrainer)
# --- NEW: TRUE INCREMENTAL ACCUMULATOR (FIXED) ---
class IncrementalRiverTrainer(pw.BaseCustomAccumulator):
    def __init__(self, row_data=None, model=None, feature_dict=None, count=0):
        # row_data: Holds the tuple (date, close, ...) if this is a new "delta"
        self.row_data = row_data

        # State: Holds the model and stats if this is the main "state"
        self.model = model
        self.feature_dict = feature_dict if feature_dict else {}
        self.count = count

    @classmethod
    def from_row(cls, row):
        # 1. Pathway calls this for every new row
        # 2. We return a "Delta" accumulator that just holds the data
        return cls(row_data=row)

    def _init_model(self):
        """Initialize the River pipeline if it doesn't exist."""
        if self.model is None:
            self.model = compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.LinearRegression(optimizer=optim.SGD(0.01), l2=0.001),
            )

    def _learn_from_row(self, row):
        """Helper to parse the row tuple and train the model."""
        (date, close, lag1, lag2, body, rng, avg_body, avg_rng, target) = row

        # 1. Update latest features (for forecasting)
        self.feature_dict = {
            "last_date": date.isoformat() if hasattr(date, "isoformat") else str(date),
            "last_close": close,
            "last_return": lag1,
            "last_lag_1_return": lag2,
            "last_body": body,
            "last_range": rng,
            "last_avg_body_14": avg_body,
            "last_avg_range_14": avg_rng,
        }

        # 2. Incremental Train (only if we have a valid target)
        if target is not None:
            x = {
                "lag_1_return": lag1,
                "lag_2_return": lag2,
                "body": body,
                "range": rng,
                "avg_body_14": avg_body,
                "avg_range_14": avg_rng,
                "current_close": close,
            }
            self.model.learn_one(x, target)
            self.count += 1

    def update(self, other):
        # 1. Ensure 'self' is a fully initialized state
        self._init_model()

        # 2. If 'self' was just created from a row, process its own data first
        if self.row_data is not None:
            self._learn_from_row(self.row_data)
            self.row_data = None  # Mark as consumed

        # 3. Process the new data coming from 'other' (the delta)
        if other.row_data is not None:
            self._learn_from_row(other.row_data)

        # Note: In a streaming groupby, 'other' is typically a delta with 1 row.

    def retract(self, other):
        # River models cannot "unlearn", so we ignore retractions
        pass

    def compute_result(self):
        # Handle case where compute_result is called on a fresh single-row accumulator
        self._init_model()
        if self.row_data is not None:
            self._learn_from_row(self.row_data)
            self.row_data = None

        lr = self.model["LinearRegression"]
        scaler = self.model["StandardScaler"]

        return {
            "trained": self.count > 0,
            "weights": dict(lr.weights),
            "intercept": float(lr.intercept),
            "scaler_means": dict(scaler.means),
            "scaler_vars": dict(scaler.vars),
            "last_features": self.feature_dict,
        }


# Register the new reducer
incremental_model_reducer = pw.reducers.udf_reducer(IncrementalRiverTrainer)

# class TrainingDataAccumulator(pw.BaseCustomAccumulator):
#     def __init__(self, records):
#         from collections import deque
#         self.records = deque(records, maxlen=LOOKBACK_DAYS)
#     @classmethod
#     def from_row(cls, row): return cls([tuple(row)])
#     def update(self, other): self.records.extend(other.records)
#     def retract(self, other): pass
#     def compute_result(self):
#         if len(self.records) < 30: return {'ready': False}
#         sorted_records = sorted(self.records, key=lambda x: x[0])
#         training_samples = []
#         for i in range(len(sorted_records) - 1):
#             curr = sorted_records[i]
#             next_close = sorted_records[i+1][1]
#             target = (next_close - curr[1]) / curr[1] if curr[1] != 0 else 0.0
#             training_samples.append({
#                 'lag_1_return': curr[2], 'lag_2_return': curr[3], 'body': curr[4],
#                 'range': curr[5], 'avg_body_14': curr[6], 'avg_range_14': curr[7],
#                 'current_close': curr[1], 'target': target
#             })

#         last = sorted_records[-1]
#         return {
#             'ready': True, 'training_samples': training_samples,
#             'last_features': {
#                 'last_date': last[0], 'last_close': last[1], 'last_return': last[2],
#                 'last_lag_1_return': last[3], 'last_body': last[4], 'last_range': last[5],
#                 'last_avg_body_14': last[6], 'last_avg_range_14': last[7]
#             }
#         }
# training_reducer = pw.reducers.udf_reducer(TrainingDataAccumulator)


@pw.udf
def parse_date_to_datetime(date_str: str) -> pw.DateTimeNaive | None:
    try:
        return datetime.fromisoformat(date_str)
    except:
        try:
            return datetime.strptime(date_str, "%m/%d/%Y")
        except:
            return None


@pw.udf
def calculate_return(curr, prev):
    return (curr - prev) / prev if prev and curr else None


@pw.udf(deterministic=True, return_type=pw.Json)
def generate_forecast(model_dict, maturity):
    if hasattr(model_dict, "as_dict"):
        model_dict = model_dict.as_dict()
    if not model_dict.get("trained", False):
        return {"forecasts": []}

    weights, intercept = model_dict["weights"], model_dict["intercept"]
    scaler_means, scaler_vars = (
        model_dict.get("scaler_means", {}),
        model_dict.get("scaler_vars", {}),
    )
    last = model_dict["last_features"]

    def predict_return(feat):
        scaled = {
            k: (v - scaler_means.get(k, 0)) / (scaler_vars.get(k, 1) ** 0.5 or 1)
            for k, v in feat.items()
        }
        return intercept + sum(weights.get(k, 0) * v for k, v in scaled.items())

    curr_yield, lag_1, lag_2 = (
        last["last_close"],
        last["last_return"],
        last["last_lag_1_return"],
    )
    try:
        current_date = datetime.fromisoformat(last["last_date"])
    except:
        return {"forecasts": []}

    results = []
    for i in range(FORECAST_DAYS):
        x = {
            "lag_1_return": lag_1,
            "lag_2_return": lag_2,
            "body": last.get("last_body", 0),
            "range": last.get("last_range", 0),
            "avg_body_14": last["last_avg_body_14"],
            "avg_range_14": last["last_avg_range_14"],
            "current_close": curr_yield,
        }

        pred_ret = max(min(predict_return(x), 0.10), -0.10)
        curr_yield = curr_yield * (1 + pred_ret)

        current_date += timedelta(days=1)
        while current_date.weekday() >= 5:
            current_date += timedelta(days=1)

        results.append(
            {
                "date": current_date.strftime("%m-%d-%Y"),
                "predicted_close": float(curr_yield),
                "predicted_return": float(pred_ret),
            }
        )
        lag_2, lag_1 = lag_1, pred_ret

    return {"maturity": maturity, "forecasts": results}


@pw.udf
def get_forecast_day(data, idx):
    d = data.as_dict() if hasattr(data, "as_dict") else data
    return d["forecasts"][idx]["date"] if 0 <= idx < len(d.get("forecasts", [])) else ""


@pw.udf
def get_predicted_close(data, idx):
    d = data.as_dict() if hasattr(data, "as_dict") else data
    return (
        float(d["forecasts"][idx]["predicted_close"])
        if 0 <= idx < len(d.get("forecasts", []))
        else 0.0
    )


@pw.udf
def get_predicted_return(data, idx):
    d = data.as_dict() if hasattr(data, "as_dict") else data
    return (
        float(d["forecasts"][idx]["predicted_return"])
        if 0 <= idx < len(d.get("forecasts", []))
        else 0.0
    )


@pw.udf
def clean_currency_string(val: str) -> float:
    try:
        return float(str(val).replace("%", "").strip())
    except:
        return 0.0


@pw.udf
def get_maturity(data):
    d = data.as_dict() if hasattr(data, "as_dict") else data
    return int(d.get("maturity", 0))


def build_hybrid_feature_pipeline(stream):
    base = stream.select(
        date=parse_date_to_datetime(pw.this.date),
        open=pw.this.open,
        high=pw.this.high,
        low=pw.this.low,
        close=pw.this.close,
        maturity=pw.this.maturity,
    )
    base = base.filter(pw.this.date.is_not_none())
    sorted_data = base.sort(pw.this.date) + base

    basic = sorted_data.with_columns(
        body=pw.this.close - pw.this.open,
        range_val=pw.this.high - pw.this.low,
        date_minus_1d=pw.this.date - timedelta(days=1),
        date_minus_2d=pw.this.date - timedelta(days=2),
    )

    # 1. First Join: Get lag_1 AND carry forward date_minus_2d
    with_lag1 = basic.asof_join(
        sorted_data, basic.date_minus_1d, sorted_data.date, how=JoinMode.LEFT
    ).select(
        *pw.left,  # Keeps all columns from 'basic' (including date_minus_2d)
        close_lag_1=pw.right.close,
    )

    # 2. Second Join: Use the RESULT of the first join (with_lag1)
    # Note: We use pw.this.date_minus_2d because it is now part of 'with_lag1'
    with_lags = with_lag1.asof_join(
        sorted_data,
        with_lag1.date_minus_2d,  # Use the column from the INTERMEDIATE table
        sorted_data.date,
        how=JoinMode.LEFT,
    ).select(*pw.left, close_lag_2=pw.right.close)
    with_rets = with_lags.with_columns(
        lag_1_return=calculate_return(pw.this.close, pw.this.close_lag_1),
        lag_2_return=calculate_return(pw.this.close_lag_1, pw.this.close_lag_2),
    )

    daily_win = with_rets.windowby(
        with_rets.date,
        window=pw.temporal.sliding(hop=timedelta(days=1), duration=timedelta(days=14)),
        instance=with_rets.maturity,
        behavior=pw.temporal.exactly_once_behavior(),
    )

    avg_body = daily_win.reduce(
        window_end=pw.this._pw_window_end,
        maturity=pw.this._pw_instance,
        avg_body_14=pw.reducers.avg(pw.coalesce(pw.this.body, 0.0)),
    )
    avg_range = daily_win.reduce(
        window_end=pw.this._pw_window_end,
        maturity=pw.this._pw_instance,
        avg_range_14=pw.reducers.avg(pw.coalesce(pw.this.range_val, 0.0)),
    )

    # We use a trick to join window results back: assume window_end aligns with daily processing
    feats = (
        with_rets.with_columns(
            daily_key=pw.apply_with_type(
                lambda dt: dt.replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=1),
                pw.DateTimeNaive,  # <--- Explicitly specify return type
                pw.this.date,
            )
        )
        .join(avg_body, pw.this.daily_key == avg_body.window_end, how=JoinMode.LEFT)
        .select(*pw.left, avg_body_14=pw.right.avg_body_14)
        .join(avg_range, pw.this.daily_key == avg_range.window_end, how=JoinMode.LEFT)
        .select(*pw.left, avg_range_14=pw.right.avg_range_14)
    )
    # final = feats.filter(
    #     pw.this.close.is_not_none() &
    #     pw.this.lag_1_return.is_not_none() &
    #     pw.this.lag_2_return.is_not_none() &
    #     pw.this.body.is_not_none() &
    #     pw.this.range_val.is_not_none() &
    #     pw.this.avg_body_14.is_not_none() &
    #     pw.this.avg_range_14.is_not_none()
    # )
    # training = final.windowby(final.date, window=pw.temporal.sliding(duration=timedelta(days=LOOKBACK_DAYS), hop=timedelta(days=1)),
    #                         instance=final.maturity, behavior=pw.temporal.exactly_once_behavior()) \
    #                 .reduce(maturity=pw.this._pw_instance, date=pw.reducers.max(pw.this.date),
    #                         data_dict=training_reducer(pw.this.date, pw.this.close, pw.this.lag_1_return, pw.this.lag_2_return,
    #                                                  pw.this.body, pw.this.range_val, pw.this.avg_body_14, pw.this.avg_range_14))

    # models = training.windowby(training.date, window=pw.temporal.tumbling(duration=timedelta(days=1)), instance=training.maturity, behavior=pw.temporal.exactly_once_behavior()) \
    #  .reduce(maturity=pw.this._pw_instance, date=pw.reducers.max(pw.this.date), model=model_reducer(pw.this.data_dict))
    # This creates a persistent group per maturity. The model in the reducer lives forever.
    # models = final.groupby(final.maturity).reduce(
    #     maturity=final.maturity,
    #     date=pw.reducers.max(final.date), # Tracks latest update
    #     model=incremental_model_reducer(
    #         final.date, final.close, final.lag_1_return, final.lag_2_return,
    #         final.body, final.range_val, final.avg_body_14, final.avg_range_14,
    #         final.target_return
    #     )
    # )
    feats_with_target = feats.with_columns(
        date_plus_1d=pw.this.date + timedelta(days=1)
    )

    # Get next close to calculate target return
    training_set = (
        feats_with_target.asof_join(
            sorted_data,
            feats_with_target.date_plus_1d,
            sorted_data.date,
            how=JoinMode.LEFT,
        )
        .select(*pw.left, next_close=pw.right.close)
        .with_columns(target_return=calculate_return(pw.this.next_close, pw.this.close))
    )

    final = training_set.filter(
        pw.this.close.is_not_none()
        & pw.this.lag_1_return.is_not_none()
        & pw.this.lag_2_return.is_not_none()
        & pw.this.body.is_not_none()
        & pw.this.range_val.is_not_none()
        & pw.this.avg_body_14.is_not_none()
        & pw.this.avg_range_14.is_not_none()
    )

    # --- CHANGED: GROUPBY instead of WINDOWBY ---
    # This creates a persistent group per maturity. The model in the reducer lives forever.
    models = final.groupby(final.maturity).reduce(
        maturity=final.maturity,
        date=pw.reducers.max(final.date),  # Tracks latest update
        model=incremental_model_reducer(
            final.date,
            final.close,
            final.lag_1_return,
            final.lag_2_return,
            final.body,
            final.range_val,
            final.avg_body_14,
            final.avg_range_14,
            final.target_return,
        ),
    )

    return models


# ==================== MAIN EXECUTION ====================


def main():
    """logger.info("STARTING PATHWAY PRODUCER...")
    rdkafka_settings = get_rdkafka_settings()"""

    # --- 1. Process Bonds (CSV + Kafka) ---
    logger.info("Processing Bond Data...")
    csv_table = pw.io.csv.read(CSV_FILE, schema=BondSchema, mode="static")
    kafka_table = pw.Table.empty(
        SYMBOL=str,
        ISIN=str,
        **{"ISIN Description": str, "Maturity Date": str, "FACE VALUE": float},
        LTP=float,
    )
    raw_combined = pw.Table.concat_reindex(csv_table, kafka_table)
    final_bonds_table = preprocess_bonds(raw_combined)

    # OUTPUT 1: Write clean bonds to disk
    pw.io.csv.write(final_bonds_table, os.path.join(OUTPUT_DIR, "bonds_snapshot.csv"))

    # --- 2. Process Yields & Forecasts ---
    logger.info("Processing Yield Forecasts...")
    tables = []

    for mat, fname in INPUT_FILES.items():
        df = pd.read_csv(fname)
        try:
            last_ts = pd.to_datetime(df["Date"], dayfirst=False).max()
        except:
            last_ts = pd.to_datetime(df["Date"], dayfirst=True).max()
        if os.path.exists(fname):
            logger.info(f"Adding stream for {mat}Y maturity")
            stream = pw.io.python.read(
                YieldStreamSubject(mat, fname, 0.0001),
                schema=YieldSchema,
                autocommit_duration_ms=100,
            )
            # kafka_sub = pw.io.kafka.read(
            #     rdkafka_settings=rdkafka_settings,
            #     topic=KAFKA_TOPIC_RAW_YIELDS,
            #     format="json",
            #     autocommit_duration_ms=1000,
            #     )
            # kafka_sub = kafka_yields.filter(pw.this.maturity == mat)
            kafka_sub = pw.Table.empty(
                date=str,
                open=float,
                **{"high": float, "low": float, "close": float},
                maturity=int,
            )
            combined_stream = pw.Table.concat_reindex(stream, kafka_sub)
            model_table = build_hybrid_feature_pipeline(combined_stream)
            final_model = model_table.filter(pw.this.date == last_ts)
            # Forecast generation (Apply model)
            forecast_table = final_model.select(
                maturity=pw.this.maturity,
                forecast_date=pw.this.date,
                forecast_data=generate_forecast(pw.this.model, pw.this.maturity),
            )
            tables.append(forecast_table)
    if tables:
        combined_forecasts = tables[0]
        for t in tables[1:]:
            combined_forecasts = combined_forecasts.concat_reindex(t)
        # Unpack JSON forecasts into rows
        output_rows = []
        for d in range(FORECAST_DAYS):
            output_rows.append(
                combined_forecasts.select(
                    Maturity=get_maturity(pw.this.forecast_data),
                    Forecast_Generation_Date=pw.this.forecast_date,
                    Prediction_Day=d + 1,
                    Target_Date=get_forecast_day(pw.this.forecast_data, d),
                    Predicted_Yield=get_predicted_close(pw.this.forecast_data, d),
                    Predicted_Return=get_predicted_return(
                        pw.this.forecast_data, d
                    ),  # <--- ADDED COLUMN HERE
                )
            )

        final_output = output_rows[0]
        for r in output_rows[1:]:
            final_output = final_output.concat_reindex(r)
        pw.debug.compute_and_print(final_output)
        # OUTPUT 2: Write forecasts to disk
        pw.io.csv.write(final_output, os.path.join(OUTPUT_DIR, "final_forecasts.csv"))

        logger.info("Pipeline built. Starting execution loop...")
        pw.run()
    else:
        logger.error("No input files found.")


if __name__ == "__main__":
    main()
