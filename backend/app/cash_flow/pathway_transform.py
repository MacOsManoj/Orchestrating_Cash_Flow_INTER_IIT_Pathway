"""
Pathway Real-Time Cash Flow Feature Engineering Pipeline

This module transforms raw bank transaction data into ML-ready features
using Pathway's streaming processing engine.
"""

import pathway as pw
from datetime import timedelta

# Set Pathway license key
pw.set_license_key("A311E3-DB2893-6F1E5B-4576CE-8C11B3-V3")


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================


class TransactionSchema(pw.Schema):
    """Schema for raw bank transaction data."""

    account_id: int
    date: str
    type: str
    operation: str
    amount: float
    balance: float
    k_symbol: str
    bank: str | None
    account: str | None
    closing_cash_balance: float | None
    opening_cash_balance: float | None


# =============================================================================
# FEATURE ENGINEERING UDFs
# =============================================================================


@pw.udf
def parse_date(date_str: str) -> pw.DateTimeNaive:
    """Parse date string to Pathway datetime (naive, no timezone)."""
    from datetime import datetime

    return datetime.strptime(date_str, "%Y-%m-%d")


@pw.udf
def compute_history_features(
    types: tuple,
    operations: tuple,
    amounts: tuple,
    balances: tuple,
    k_symbols: tuple,
    banks: tuple,
    accounts: tuple,
    account_ids: tuple,
) -> dict:
    """
    Compute all window features in a single UDF.
    This mirrors the original pandas implementation closely.
    """
    import numpy as np

    # Convert tuples to lists for easier manipulation
    types = list(types)
    operations = list(operations)
    amounts = list(amounts)
    balances = list(balances)
    k_symbols = list(k_symbols)
    banks = list(banks)
    accounts = list(accounts)
    account_ids = list(account_ids)

    n = len(types)
    if n == 0:
        return {
            "income_amount": 0.0,
            "expense_amount": 0.0,
            "withdrawal_amount": 0.0,
            "balance_mean": 0.0,
            "balance_median": 0.0,
            "balance_std": 0.0,
            "balance_eod": 0.0,
            "amount_mean": 0.0,
            "amount_median": 0.0,
            "amount_std": 0.0,
            "amount_min": 0.0,
            "amount_max": 0.0,
            "type_INCOME_count": 0,
            "type_EXPENSE_count": 0,
            "type_WITHDRAWAL_count": 0,
            "operation_DEPOSIT_count": 0,
            "operation_WITHDRAWAL_count": 0,
            "operation_CARD WITHDRAWAL_count": 0,
            "operation_TRANSFER TO ACCOUNT_count": 0,
            "operation_TRANSFER FROM ACCOUNT_count": 0,
            "k_symbol_PENSION_count": 0,
            "k_symbol_INTEREST_count": 0,
            "k_symbol_SIPO PAYMENT_count": 0,
            "k_symbol_SERVICES_count": 0,
            "k_symbol_INSURANCE_count": 0,
            "k_symbol_LOAN_count": 0,
            "k_symbol_PENALTY INTEREST_count": 0,
            "k_symbol_UNKNOWN_count": 0,
            "unique_bank_count": 0,
            "unique_transfer_account_count": 0,
            "unique_account_id_count": 0,
        }

    # Financial Aggregates
    income_amount = sum(a for t, a in zip(types, amounts) if t == "INCOME")
    expense_amount = sum(a for t, a in zip(types, amounts) if t == "EXPENSE")
    withdrawal_amount = sum(a for t, a in zip(types, amounts) if t == "WITHDRAWAL")

    # Balance stats
    balance_arr = np.array(balances)
    amount_arr = np.array(amounts)

    features = {
        "income_amount": float(income_amount),
        "expense_amount": float(expense_amount),
        "withdrawal_amount": float(withdrawal_amount),
        "balance_mean": float(np.mean(balance_arr)),
        "balance_median": float(np.median(balance_arr)),
        "balance_std": float(np.std(balance_arr, ddof=1)) if n > 1 else 0.0,
        "balance_eod": float(balances[-1]),  # Last balance (assuming sorted)
        "amount_mean": float(np.mean(amount_arr)),
        "amount_median": float(np.median(amount_arr)),
        "amount_std": float(np.std(amount_arr, ddof=1)) if n > 1 else 0.0,
        "amount_min": float(np.min(amount_arr)),
        "amount_max": float(np.max(amount_arr)),
        # Type counts
        "type_INCOME_count": sum(1 for t in types if t == "INCOME"),
        "type_EXPENSE_count": sum(1 for t in types if t == "EXPENSE"),
        "type_WITHDRAWAL_count": sum(1 for t in types if t == "WITHDRAWAL"),
        # Operation counts (with spaces to match original)
        "operation_DEPOSIT_count": sum(1 for o in operations if o == "DEPOSIT"),
        "operation_WITHDRAWAL_count": sum(1 for o in operations if o == "WITHDRAWAL"),
        "operation_CARD WITHDRAWAL_count": sum(
            1 for o in operations if o == "CARD WITHDRAWAL"
        ),
        "operation_TRANSFER TO ACCOUNT_count": sum(
            1 for o in operations if o == "TRANSFER TO ACCOUNT"
        ),
        "operation_TRANSFER FROM ACCOUNT_count": sum(
            1 for o in operations if o == "TRANSFER FROM ACCOUNT"
        ),
        # k_symbol counts (with spaces to match original)
        "k_symbol_PENSION_count": sum(1 for k in k_symbols if k == "PENSION"),
        "k_symbol_INTEREST_count": sum(1 for k in k_symbols if k == "INTEREST"),
        "k_symbol_SIPO PAYMENT_count": sum(1 for k in k_symbols if k == "SIPO PAYMENT"),
        "k_symbol_SERVICES_count": sum(1 for k in k_symbols if k == "SERVICES"),
        "k_symbol_INSURANCE_count": sum(1 for k in k_symbols if k == "INSURANCE"),
        "k_symbol_LOAN_count": sum(1 for k in k_symbols if k == "LOAN"),
        "k_symbol_PENALTY INTEREST_count": sum(1 for k in k_symbols if k == "PENALTY"),
        "k_symbol_UNKNOWN_count": sum(1 for k in k_symbols if k == "UNKNOWN"),
        # Network features
        "unique_bank_count": len(set(b for b in banks if b is not None and b != "")),
        "unique_transfer_account_count": len(
            set(a for a in accounts if a is not None and a != "")
        ),
        "unique_account_id_count": len(set(account_ids)),
    }

    return features


@pw.udf
def compute_target_cashflow(types: tuple, amounts: tuple) -> float:
    """Compute the target cash flow for prediction window."""
    income = sum(a for t, a in zip(types, amounts) if t == "INCOME")
    expense = sum(a for t, a in zip(types, amounts) if t == "EXPENSE")
    withdrawal = sum(a for t, a in zip(types, amounts) if t == "WITHDRAWAL")
    return float(income - expense - withdrawal)


@pw.udf
def extract_year(dt: pw.DateTimeNaive) -> int:
    return dt.year


@pw.udf
def extract_month(dt: pw.DateTimeNaive) -> int:
    return dt.month


@pw.udf
def extract_day(dt: pw.DateTimeNaive) -> int:
    return dt.day


# =============================================================================
# WINDOW FEATURE CREATION
# =============================================================================


def create_window_features(
    transactions: pw.Table, history_window_days: int, prediction_window_days: int
) -> pw.Table:
    """
    Create sliding window features for cash flow prediction using UDF approach.
    """

    # Parse dates and add timestamp column
    transactions = transactions.with_columns(timestamp=parse_date(pw.this.date))

    history_window = timedelta(days=history_window_days)

    # Use temporal windowby for sliding window aggregations
    windowed = transactions.windowby(
        transactions.timestamp,
        window=pw.temporal.sliding(duration=history_window, hop=timedelta(days=1)),
        behavior=pw.temporal.common_behavior(
            cutoff=timedelta(days=prediction_window_days)
        ),
    )

    # Collect all values using tuple reducer, then compute features via UDF
    collected = windowed.reduce(
        window_start=pw.this._pw_window_start,
        window_end=pw.this._pw_window_end,
        types=pw.reducers.tuple(pw.this.type),
        operations=pw.reducers.tuple(pw.this.operation),
        amounts=pw.reducers.tuple(pw.this.amount),
        balances=pw.reducers.tuple(pw.this.balance),
        k_symbols=pw.reducers.tuple(pw.this.k_symbol),
        banks=pw.reducers.tuple(pw.this.bank),
        accounts=pw.reducers.tuple(pw.this.account),
        account_ids=pw.reducers.tuple(pw.this.account_id),
    )

    # Compute all features using UDF
    features = collected.with_columns(
        features=compute_history_features(
            pw.this.types,
            pw.this.operations,
            pw.this.amounts,
            pw.this.balances,
            pw.this.k_symbols,
            pw.this.banks,
            pw.this.accounts,
            pw.this.account_ids,
        ),
        # Extract date components
        history_window_start_year=extract_year(pw.this.window_start),
        history_window_start_month=extract_month(pw.this.window_start),
        history_window_start_day=extract_day(pw.this.window_start),
        history_window_end_year=extract_year(pw.this.window_end),
        history_window_end_month=extract_month(pw.this.window_end),
        history_window_end_day=extract_day(pw.this.window_end),
    )

    # Unpack the features dictionary into columns
    features = features.select(
        window_start=pw.this.window_start,
        window_end=pw.this.window_end,
        history_window_start_year=pw.this.history_window_start_year,
        history_window_start_month=pw.this.history_window_start_month,
        history_window_start_day=pw.this.history_window_start_day,
        history_window_end_year=pw.this.history_window_end_year,
        history_window_end_month=pw.this.history_window_end_month,
        history_window_end_day=pw.this.history_window_end_day,
        income_amount=pw.this.features["income_amount"],
        expense_amount=pw.this.features["expense_amount"],
        withdrawal_amount=pw.this.features["withdrawal_amount"],
        balance_mean=pw.this.features["balance_mean"],
        balance_median=pw.this.features["balance_median"],
        balance_std=pw.this.features["balance_std"],
        balance_eod=pw.this.features["balance_eod"],
        amount_mean=pw.this.features["amount_mean"],
        amount_median=pw.this.features["amount_median"],
        amount_std=pw.this.features["amount_std"],
        amount_min=pw.this.features["amount_min"],
        amount_max=pw.this.features["amount_max"],
        type_INCOME_count=pw.this.features["type_INCOME_count"],
        type_EXPENSE_count=pw.this.features["type_EXPENSE_count"],
        type_WITHDRAWAL_count=pw.this.features["type_WITHDRAWAL_count"],
        operation_DEPOSIT_count=pw.this.features["operation_DEPOSIT_count"],
        operation_WITHDRAWAL_count=pw.this.features["operation_WITHDRAWAL_count"],
        **{
            "operation_CARD WITHDRAWAL_count": pw.this.features[
                "operation_CARD WITHDRAWAL_count"
            ]
        },
        **{
            "operation_TRANSFER TO ACCOUNT_count": pw.this.features[
                "operation_TRANSFER TO ACCOUNT_count"
            ]
        },
        **{
            "operation_TRANSFER FROM ACCOUNT_count": pw.this.features[
                "operation_TRANSFER FROM ACCOUNT_count"
            ]
        },
        k_symbol_PENSION_count=pw.this.features["k_symbol_PENSION_count"],
        k_symbol_INTEREST_count=pw.this.features["k_symbol_INTEREST_count"],
        **{
            "k_symbol_SIPO PAYMENT_count": pw.this.features[
                "k_symbol_SIPO PAYMENT_count"
            ]
        },
        k_symbol_SERVICES_count=pw.this.features["k_symbol_SERVICES_count"],
        k_symbol_INSURANCE_count=pw.this.features["k_symbol_INSURANCE_count"],
        k_symbol_LOAN_count=pw.this.features["k_symbol_LOAN_count"],
        **{
            "k_symbol_PENALTY INTEREST_count": pw.this.features[
                "k_symbol_PENALTY INTEREST_count"
            ]
        },
        k_symbol_UNKNOWN_count=pw.this.features["k_symbol_UNKNOWN_count"],
        unique_bank_count=pw.this.features["unique_bank_count"],
        unique_transfer_account_count=pw.this.features["unique_transfer_account_count"],
        unique_account_id_count=pw.this.features["unique_account_id_count"],
    )

    return features


def create_prediction_targets(
    transactions: pw.Table, history_window_days: int, prediction_window_days: int
) -> pw.Table:
    """
    Create prediction target (future window cash flow) using UDF approach.
    """

    transactions = transactions.with_columns(timestamp=parse_date(pw.this.date))

    prediction_window = timedelta(days=prediction_window_days)

    # Window for prediction targets
    target_windowed = transactions.windowby(
        transactions.timestamp,
        window=pw.temporal.sliding(
            duration=prediction_window,
            hop=timedelta(days=1),
        ),
    )

    # Collect values and compute target via UDF
    collected = target_windowed.reduce(
        window_start=pw.this._pw_window_start,
        window_end=pw.this._pw_window_end,
        types=pw.reducers.tuple(pw.this.type),
        amounts=pw.reducers.tuple(pw.this.amount),
    )

    targets = collected.with_columns(
        target_next_window_cashflow=compute_target_cashflow(
            pw.this.types,
            pw.this.amounts,
        ),
        prediction_window_start_year=extract_year(pw.this.window_start),
        prediction_window_start_month=extract_month(pw.this.window_start),
        prediction_window_start_day=extract_day(pw.this.window_start),
        prediction_window_end_year=extract_year(pw.this.window_end),
        prediction_window_end_month=extract_month(pw.this.window_end),
        prediction_window_end_day=extract_day(pw.this.window_end),
    )

    return targets.select(
        window_start=pw.this.window_start,
        window_end=pw.this.window_end,
        prediction_window_start_year=pw.this.prediction_window_start_year,
        prediction_window_start_month=pw.this.prediction_window_start_month,
        prediction_window_start_day=pw.this.prediction_window_start_day,
        prediction_window_end_year=pw.this.prediction_window_end_year,
        prediction_window_end_month=pw.this.prediction_window_end_month,
        prediction_window_end_day=pw.this.prediction_window_end_day,
        target_next_window_cashflow=pw.this.target_next_window_cashflow,
    )


def add_lag_features(dataset: pw.Table, num_lags: int = 7) -> pw.Table:
    """
    Add lagged target values as features using temporal self-joins.
    """
    result = dataset

    for lag in range(1, num_lags + 1):
        lag_offset = timedelta(days=lag)

        # Create a table with shifted window_end for joining
        lagged = dataset.select(
            window_end_shifted=pw.this.window_end + lag_offset,
            lag_value=pw.this.target_next_window_cashflow,
        )

        # Join on shifted window end
        result = result.join_left(
            lagged, pw.left.window_end == pw.right.window_end_shifted
        ).select(
            *pw.left, **{f"target_next_window_cashflow_lag_{lag}": pw.right.lag_value}
        )

    return result


# =============================================================================
# MAIN PIPELINE
# =============================================================================


def build_cashflow_pipeline(
    input_path: str,
    output_path: str,
    history_window_days: int = 7,
    prediction_window_days: int = 7,
    mode: str = "streaming",
    persistence_path: str | None = None,
) -> None:
    """
    Build and run the complete cash flow feature engineering pipeline.

    Args:
        input_path: Path to input CSV file or directory
        output_path: Path to output CSV file
        history_window_days: History window size in days
        prediction_window_days: Prediction window size in days
        mode: Pipeline mode - "static" or "streaming"
        persistence_path: Path to store persistence state (enables checkpoint/recovery)
    """

    # Configure persistence if path provided
    persistence_config = None
    if persistence_path:
        persistence_backend = pw.persistence.Backend.filesystem(persistence_path)
        persistence_config = pw.persistence.Config(persistence_backend)
        print(f"Persistence enabled: {persistence_path}")

    # Read input data with unique name for persistence matching
    if mode == "streaming":
        transactions = pw.io.csv.read(
            input_path,
            schema=TransactionSchema,
            mode="streaming",
            autocommit_duration_ms=1000,
            name="transactions_source",  # Unique name for persistence
        )
    else:
        transactions = pw.io.csv.read(
            input_path,
            schema=TransactionSchema,
            mode="static",
            name="transactions_source",  # Unique name for persistence
        )

    # Create history window features
    features = create_window_features(
        transactions, history_window_days, prediction_window_days
    )

    # Create prediction targets
    targets = create_prediction_targets(
        transactions, history_window_days, prediction_window_days
    )

    # Join features with targets based on window alignment
    # History window end should match prediction window start
    dataset = features.join(
        targets, pw.left.window_end == pw.right.window_start
    ).select(
        # Date components in expected order
        history_window_start_year=pw.left.history_window_start_year,
        history_window_start_month=pw.left.history_window_start_month,
        history_window_start_day=pw.left.history_window_start_day,
        history_window_end_year=pw.left.history_window_end_year,
        history_window_end_month=pw.left.history_window_end_month,
        history_window_end_day=pw.left.history_window_end_day,
        prediction_window_start_year=pw.right.prediction_window_start_year,
        prediction_window_start_month=pw.right.prediction_window_start_month,
        prediction_window_start_day=pw.right.prediction_window_start_day,
        prediction_window_end_year=pw.right.prediction_window_end_year,
        prediction_window_end_month=pw.right.prediction_window_end_month,
        prediction_window_end_day=pw.right.prediction_window_end_day,
        # Features
        income_amount=pw.left.income_amount,
        expense_amount=pw.left.expense_amount,
        withdrawal_amount=pw.left.withdrawal_amount,
        balance_mean=pw.left.balance_mean,
        balance_median=pw.left.balance_median,
        balance_std=pw.left.balance_std,
        balance_eod=pw.left.balance_eod,
        amount_mean=pw.left.amount_mean,
        amount_median=pw.left.amount_median,
        amount_std=pw.left.amount_std,
        amount_min=pw.left.amount_min,
        amount_max=pw.left.amount_max,
        type_INCOME_count=pw.left.type_INCOME_count,
        type_EXPENSE_count=pw.left.type_EXPENSE_count,
        type_WITHDRAWAL_count=pw.left.type_WITHDRAWAL_count,
        operation_DEPOSIT_count=pw.left.operation_DEPOSIT_count,
        operation_WITHDRAWAL_count=pw.left.operation_WITHDRAWAL_count,
        **{
            "operation_CARD WITHDRAWAL_count": pw.left[
                "operation_CARD WITHDRAWAL_count"
            ]
        },
        **{
            "operation_TRANSFER TO ACCOUNT_count": pw.left[
                "operation_TRANSFER TO ACCOUNT_count"
            ]
        },
        **{
            "operation_TRANSFER FROM ACCOUNT_count": pw.left[
                "operation_TRANSFER FROM ACCOUNT_count"
            ]
        },
        k_symbol_PENSION_count=pw.left.k_symbol_PENSION_count,
        k_symbol_INTEREST_count=pw.left.k_symbol_INTEREST_count,
        **{"k_symbol_SIPO PAYMENT_count": pw.left["k_symbol_SIPO PAYMENT_count"]},
        k_symbol_SERVICES_count=pw.left.k_symbol_SERVICES_count,
        k_symbol_INSURANCE_count=pw.left.k_symbol_INSURANCE_count,
        k_symbol_LOAN_count=pw.left.k_symbol_LOAN_count,
        **{
            "k_symbol_PENALTY INTEREST_count": pw.left[
                "k_symbol_PENALTY INTEREST_count"
            ]
        },
        k_symbol_UNKNOWN_count=pw.left.k_symbol_UNKNOWN_count,
        unique_bank_count=pw.left.unique_bank_count,
        unique_transfer_account_count=pw.left.unique_transfer_account_count,
        unique_account_id_count=pw.left.unique_account_id_count,
        # Target
        target_next_window_cashflow=pw.right.target_next_window_cashflow,
        # Keep window_end for lag joins
        window_end=pw.left.window_end,
    )

    # Add lag features
    dataset = add_lag_features(dataset, num_lags=7)

    # Remove window_end from final output (not in original)
    dataset = dataset.without(pw.this.window_end)

    # Output results
    pw.io.csv.write(dataset, output_path)

    # Run the pipeline with optional persistence
    pw.run(persistence_config=persistence_config)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Pathway Cash Flow Feature Engineering Pipeline"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="streaming-bank-data/streaming-bank-data-new/bank-data-raw-new-test.csv",
        help="Input CSV file path",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output CSV file path (auto-generated if not provided)",
    )
    parser.add_argument(
        "--history-days", "-H", type=int, default=7, help="History window size in days"
    )
    parser.add_argument(
        "--prediction-days",
        "-P",
        type=int,
        default=7,
        help="Prediction window size in days",
    )
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        default="static",
        choices=["static", "streaming"],
        help="Pipeline mode: static or streaming",
    )
    parser.add_argument(
        "--persistence",
        "-p",
        type=str,
        default=None,
        help="Path to store persistence state for checkpoint/recovery (e.g., ./pipeline_state/)",
    )

    args = parser.parse_args()

    # Auto-generate output path if not provided
    if args.output is None:
        input_dir = os.path.dirname(args.input)
        args.output = os.path.join(
            input_dir, f"dataset_H{args.history_days}_F{args.prediction_days}_new.csv"
        )

    print(f"Running pipeline: H{args.history_days}_F{args.prediction_days}")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Mode: {args.mode}")
    if args.persistence:
        print(f"Persistence: {args.persistence}")

    build_cashflow_pipeline(
        input_path=args.input,
        output_path=args.output,
        history_window_days=args.history_days,
        prediction_window_days=args.prediction_days,
        mode=args.mode,
        persistence_path=args.persistence,
    )
