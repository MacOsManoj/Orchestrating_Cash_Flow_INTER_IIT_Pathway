import pandas as pd
import joblib
import os
import shap
import numpy as np


def get_cashflow_prediction(window_size):
    """
    Load a model for the specified window size and make a prediction using the most recent datapoint.

    Args:
        window_size (int): Window size in days. Must be one of: 1, 3, 5, 7, 14, or 30.

    Returns:
        float: Predicted cashflow for the next window period.

    Raises:
        ValueError: If window_size is not one of the supported values.
        FileNotFoundError: If model or dataset file is not found.
    """
    # Validate window size
    valid_window_sizes = [1, 3, 5, 7, 14, 30]
    if window_size not in valid_window_sizes:
        raise ValueError(
            f"Window size must be one of {valid_window_sizes}, got {window_size}"
        )

    # Define base paths
    base_dir = "./app/cash_flow"
    models_dir = os.path.join(base_dir, "cash-flow-models")
    data_dir = os.path.join(base_dir, "streaming-bank-data")

    # Map window size to model file pattern
    # Models are named like: best_{Model_Type}_{Model_Name}_H{window_size}_F{window_size}.pkl
    model_pattern = f"*_H{window_size}_F{window_size}.pkl"

    # Find the model file
    import glob

    model_files = glob.glob(os.path.join(models_dir, model_pattern))

    if not model_files:
        raise FileNotFoundError(
            f"No model found for window size {window_size} in {models_dir}"
        )

    # Use the first matching model file
    model_path = model_files[0]
    # print(f"Loading model: {os.path.basename(model_path)}")

    # Load the model
    model = joblib.load(model_path)

    # Load the appropriate dataset file
    dataset_file = os.path.join(data_dir, f"dataset_H{window_size}_F{window_size}.csv")

    if not os.path.exists(dataset_file):
        raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

    # print(f"Loading dataset: {os.path.basename(dataset_file)}")
    df = pd.read_csv(dataset_file)

    # Get the most recent datapoint (last row)
    last_row = df.iloc[-1:].copy()

    # Drop the target column (matching the training code: X = df_temp.drop(columns=[target_col]))
    target_col = "target_next_window_cashflow"
    X_pred = last_row.drop(columns=[target_col], errors="ignore")

    # Handle any NaN values (fill with 0)
    X_pred = X_pred.fillna(0)

    # Ensure feature order matches model expectations (if model has feature_names_in_)
    if hasattr(model, "feature_names_in_"):
        # Reorder columns to match model's expected feature order
        X_pred = X_pred[model.feature_names_in_]

    # print(f"Making prediction using {len(X_pred.columns)} features...")
    # print(f"Most recent datapoint date: {last_row['history_window_end_year'].values[0]}-{last_row['history_window_end_month'].values[0]}-{last_row['history_window_end_day'].values[0]}")

    # Make prediction
    prediction = model.predict(X_pred)[0]

    # print(f"Predicted cashflow for next {window_size}-day window: {prediction:.2f}")

    return prediction


def get_cashflow_shap_explanation(window_size, top_n=10):
    """
    Get SHAP explanation for cashflow prediction, identifying top variables that influenced the prediction.

    Args:
        window_size (int): Window size in days. Must be one of: 1, 3, 5, 7, 14, or 30.
        top_n (int): Number of top variables to return. Default is 10.

    Returns:
        list: List of dictionaries, each containing:
            - 'variable_name': Name of the feature
            - 'value': The actual value of the feature in the prediction
            - 'shap_score': SHAP value (contribution to prediction)
            - 'abs_shap_score': Absolute SHAP value (for sorting)

    Raises:
        ValueError: If window_size is not one of the supported values.
        FileNotFoundError: If model or dataset file is not found.
    """
    # Validate window size
    valid_window_sizes = [1, 3, 5, 7, 14, 30]
    if window_size not in valid_window_sizes:
        raise ValueError(
            f"Window size must be one of {valid_window_sizes}, got {window_size}"
        )

    # Define base paths
    base_dir = "./app/cash_flow"
    models_dir = os.path.join(base_dir, "cash-flow-models")
    data_dir = os.path.join(base_dir, "streaming-bank-data")

    # Find and load the model
    import glob

    model_pattern = f"*_H{window_size}_F{window_size}.pkl"
    model_files = glob.glob(os.path.join(models_dir, model_pattern))

    if not model_files:
        raise FileNotFoundError(
            f"No model found for window size {window_size} in {models_dir}"
        )

    model_path = model_files[0]
    # print(f"Loading model: {os.path.basename(model_path)}")
    model = joblib.load(model_path)

    # Load the dataset
    dataset_file = os.path.join(data_dir, f"dataset_H{window_size}_F{window_size}.csv")
    if not os.path.exists(dataset_file):
        raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

    # print(f"Loading dataset: {os.path.basename(dataset_file)}")
    df = pd.read_csv(dataset_file)

    # Get the most recent datapoint (last row)
    last_row = df.iloc[-1:].copy()

    # Prepare features (same as prediction function)
    target_col = "target_next_window_cashflow"
    X_pred = last_row.drop(columns=[target_col], errors="ignore")
    X_pred = X_pred.fillna(0)

    # Ensure feature order matches model expectations
    if hasattr(model, "feature_names_in_"):
        X_pred = X_pred[model.feature_names_in_]

    # Get a sample of background data for SHAP (use last 100 rows as background)
    # This helps SHAP understand the distribution of features
    background_data = df.tail(100).drop(columns=[target_col], errors="ignore").fillna(0)
    if hasattr(model, "feature_names_in_"):
        background_data = background_data[model.feature_names_in_]

    print(f"Computing SHAP values using {len(background_data)} background samples...")

    # Choose appropriate SHAP explainer based on model type
    model_type = type(model).__name__

    try:
        # For tree-based models, use TreeExplainer (faster and exact)
        if any(
            x in model_type
            for x in [
                "Tree",
                "Forest",
                "Boosting",
                "XGB",
                "LGBM",
                "CatBoost",
                "GradientBoosting",
                "ExtraTrees",
                "RandomForest",
            ]
        ):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_pred)
        else:
            # For linear models and others, use KernelExplainer or LinearExplainer
            if (
                "Linear" in model_type
                or "Ridge" in model_type
                or "Lasso" in model_type
                or "ElasticNet" in model_type
            ):
                explainer = shap.LinearExplainer(model, background_data)
            else:
                # Use KernelExplainer as fallback (slower but works for all models)
                explainer = shap.KernelExplainer(
                    model.predict, background_data.sample(min(50, len(background_data)))
                )
            shap_values = explainer.shap_values(X_pred)

        # Handle different return formats (some explainers return arrays)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]  # Take first output if multiple
        if len(shap_values.shape) > 1:
            shap_values = shap_values[0]  # Take first row if 2D

        # Get feature names
        feature_names = X_pred.columns.tolist()

        # Get actual feature values
        feature_values = X_pred.iloc[0].values

        # Create list of variable information
        variable_info = []
        for i, (name, value, shap_val) in enumerate(
            zip(feature_names, feature_values, shap_values)
        ):
            variable_info.append(
                {
                    "variable_name": name,
                    "value": float(value),
                    "shap_score": float(shap_val),
                    "abs_shap_score": float(abs(shap_val)),
                }
            )

        # Sort by absolute SHAP score (descending) and get top N
        variable_info.sort(key=lambda x: x["abs_shap_score"], reverse=True)
        top_variables = variable_info[:top_n]

        # print(f"\nTop {top_n} variables influencing the prediction:")
        # print("="*80)
        # for i, var in enumerate(top_variables, 1):
        #    print(f"{i:2d}. {var['variable_name']:40s} | Value: {var['value']:15.2f} | SHAP: {var['shap_score']:12.2f}")

        return top_variables

    except Exception as e:
        # print(f"Error computing SHAP values: {e}")
        # print("Attempting alternative SHAP explainer...")

        # Fallback: Try simpler approach
        try:
            # Use a smaller background sample
            small_background = background_data.sample(min(20, len(background_data)))
            explainer = shap.KernelExplainer(model.predict, small_background)
            shap_values = explainer.shap_values(X_pred.iloc[0:1])

            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            if len(shap_values.shape) > 1:
                shap_values = shap_values[0]

            feature_names = X_pred.columns.tolist()
            feature_values = X_pred.iloc[0].values

            variable_info = []
            for i, (name, value, shap_val) in enumerate(
                zip(feature_names, feature_values, shap_values)
            ):
                variable_info.append(
                    {
                        "variable_name": name,
                        "value": float(value),
                        "shap_score": float(shap_val),
                        "abs_shap_score": float(abs(shap_val)),
                    }
                )

            variable_info.sort(key=lambda x: x["abs_shap_score"], reverse=True)
            top_variables = variable_info[:top_n]

            # print(f"\nTop {top_n} variables influencing the prediction:")
            # print("="*80)
            # for i, var in enumerate(top_variables, 1):
            #    print(f"{i:2d}. {var['variable_name']:40s} | Value: {var['value']:15.2f} | SHAP: {var['shap_score']:12.2f}")

            return top_variables

        except Exception as e2:
            raise RuntimeError(f"Failed to compute SHAP values: {e2}")


def predict_liquidity_regime(
    model_path: str = "app/cash_flow/cash-flow-models/liquidity_hmm_prod.pkl",
    csv_file_path: str = "app/cash_flow/streaming-bank-data/dataset_H1_F1.csv",
) -> dict:
    """Predict the liquidity risk regime for the next trading day.

    Loads a pre-trained Hidden Markov Model (HMM) to predict the probability of the bank
    entering a 'High Liquidity Risk' regime tomorrow based on rolling liquidity indicators.

    Args:
        model_path (str, optional): Path to the HMM model checkpoint.
        csv_file_path (str, optional): Path to the bank transaction data CSV.

    Returns:
        dict: Prediction results or {"error": "..."} if input/model unavailable.
    """
    # 1. Check for Model Artifact
    if not os.path.exists(model_path):
        return {"error": f"Model artifact not found: {model_path}"}

    try:
        # 2. Check for CSV Data
        if not os.path.exists(csv_file_path):
            return {"error": f"Input file not found: {csv_file_path}"}

        # 3. Load Data & Model
        df = pd.read_csv(csv_file_path)
        checkpoint = joblib.load(model_path)

        model = checkpoint["model"]
        scaler = checkpoint["scaler"]
        risk_id = checkpoint["risk_id"]
        clip_limits = checkpoint["clip_limits"]
        window = checkpoint["buffer_window"]

        # 4. Minimal Data Requirement
        if len(df) < window:
            return {"error": f"Insufficient data. Needed {window} rows, got {len(df)}."}

        # 5. Feature Engineering
        df_subset = df.tail(window + 10).copy()

        total_vol = (
            df_subset["income_amount"]
            + df_subset["expense_amount"]
            + df_subset["withdrawal_amount"]
            + 1e-9
        )
        net_flow = df_subset["income_amount"] - (
            df_subset["expense_amount"] + df_subset["withdrawal_amount"]
        )
        df_subset["imbalance_raw"] = net_flow / total_vol

        w_ops = (
            df_subset["operation_WITHDRAWAL_count"]
            + df_subset["operation_CARD WITHDRAWAL_count"]
        )
        t_ops = df_subset["operation_DEPOSIT_count"] + w_ops + 1e-9
        df_subset["intensity_raw"] = w_ops / t_ops

        df_subset["hmm_feat_imbalance"] = (
            df_subset["imbalance_raw"].rolling(window=window).mean()
        )
        vol_raw = df_subset["imbalance_raw"].rolling(window=window).std()
        df_subset["hmm_feat_volatility"] = np.log1p(vol_raw)
        df_subset["hmm_feat_withdraw_intensity"] = (
            df_subset["intensity_raw"].rolling(window=window).mean()
        )

        last_row = df_subset.iloc[-1]
        feature_vector = np.array(
            [
                last_row["hmm_feat_imbalance"],
                last_row["hmm_feat_volatility"],
                last_row["hmm_feat_withdraw_intensity"],
            ]
        )

        # Winsorization
        feat_names = [
            "hmm_feat_imbalance",
            "hmm_feat_volatility",
            "hmm_feat_withdraw_intensity",
        ]
        for i, name in enumerate(feat_names):
            limits = clip_limits[name]
            feature_vector[i] = np.clip(feature_vector[i], limits["min"], limits["max"])

        # Scale
        features_scaled = scaler.transform(feature_vector.reshape(1, -1))

        # Predict
        current_state_prob = model.predict_proba(features_scaled)[-1]
        next_day_prob = np.dot(current_state_prob, model.transmat_)
        risk_score = next_day_prob[risk_id]

        is_alert = bool(risk_score > 0.5)
        msg = (
            "CRITICAL: High structural liquidity stress detected."
            if is_alert
            else "STATUS: Operations projected to remain normal."
        )

        return {
            "file_path": csv_file_path,
            "current_regime_prob": float(risk_score),
            "alert_status": is_alert,
            "message": msg,
            "features_used": {
                "30_day_trend": float(feature_vector[0]),
                "30_day_volatility": float(feature_vector[1]),
                "30_day_panic_index": float(feature_vector[2]),
            },
        }

    except Exception as e:
        return {"error": f"Prediction failed: {str(e)}"}
