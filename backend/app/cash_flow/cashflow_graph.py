import pandas as pd
import numpy as np


def analyze_last_28_days(file_path):
    """
    Reads the last 28 days of information from a bank data CSV and computes
    summaries for Total Deposit, Job Income, Interest, Loans, Online Withdrawal,
    and Offline Withdrawal for the last 4 weeks.

    Args:
        file_path (str): Path to the bank data CSV file.

    Returns:
        pd.DataFrame: A summary table with columns for each week and rows for each category.
    """
    # Read CSV
    # Using low_memory=False to suppress warnings about mixed types if any
    df = pd.read_csv(file_path, low_memory=False)

    # Convert date column to datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    else:
        raise ValueError("CSV must contain a 'date' column")

    # Determine the last date in the dataset
    last_date = df["date"].max()
    start_date = last_date - pd.Timedelta(days=27)  # 28 days total including end date

    # Filter for the last 28 days
    mask_28_days = (df["date"] >= start_date) & (df["date"] <= last_date)
    df_recent = df.loc[mask_28_days].copy()

    if df_recent.empty:
        print("No data found in the last 28 days.")
        return pd.DataFrame()

    # Calculate 'days_ago' to bucket into weeks
    # Week 1 (Last week): 0-6 days ago
    # Week 2 (Second last): 7-13 days ago
    # Week 3 (Third last): 14-20 days ago
    # Week 4 (Fourth last): 21-27 days ago
    df_recent["days_ago"] = (last_date - df_recent["date"]).dt.days
    df_recent["week_bucket"] = df_recent["days_ago"] // 7

    # Define categories based on user instructions
    # Deposit: operation = DEPOSIT
    # Job Income: operation = TRANSFER FROM ACCOUNT
    # Interest: operation = NaN
    # Loans: operation = TRANSFER TO ACCOUNT
    # Online Withdrawal: operation = CARD WITHDRAWAL (per specific instruction overriding standard naming)
    # Offline Withdrawal: operation = WITHDRAWAL (per specific instruction overriding standard naming)

    conditions = [
        df_recent["operation"] == "DEPOSIT",
        df_recent["operation"] == "TRANSFER FROM ACCOUNT",
        df_recent["operation"].isna(),  # Interest
        df_recent["operation"] == "TRANSFER TO ACCOUNT",
        df_recent["operation"] == "CARD WITHDRAWAL",
        df_recent["operation"] == "WITHDRAWAL",
    ]

    categories = [
        "Total Deposit",
        "Job Income",
        "Interest",
        "Loans",
        "Online Withdrawal",  # Mapped to CARD WITHDRAWAL
        "Offline Withdrawal",  # Mapped to WITHDRAWAL
    ]

    # Create a category column
    df_recent["category"] = np.select(conditions, categories, default="Other")

    # Pivot table to sum amounts by category and week
    # Columns: week_bucket (0, 1, 2, 3)
    # Index: category
    # Values: amount (sum)
    summary = df_recent.pivot_table(
        index="category",
        columns="week_bucket",
        values="amount",
        aggfunc="sum",
        fill_value=0.0,
    )

    # Rename columns for clarity
    week_names = {
        0: "Last Week",
        1: "Second Last Week",
        2: "Third Last Week",
        3: "Fourth Last Week",
    }
    summary = summary.rename(columns=week_names)

    # Ensure all target categories exist in the index, even if 0
    for cat in categories:
        if cat not in summary.index:
            summary.loc[cat] = 0.0

    # Reorder rows
    summary = summary.reindex(categories)

    # Reorder columns to ensure 0-3 order if some weeks are missing data
    desired_cols = [
        "Last Week",
        "Second Last Week",
        "Third Last Week",
        "Fourth Last Week",
    ]
    for col in desired_cols:
        if col not in summary.columns:
            summary[col] = 0.0
    summary = summary[desired_cols]

    # Convert to JSON with index orientation to preserve Category -> Week structure
    return summary.to_json(orient="index")
