from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse, FileResponse, Response
import subprocess 
import pandas as pd
import os
import json
from app.cash_flow.liquidity_risk_tools import predict_liquidity_regime
from app.cash_flow.cashflow_graph import analyze_last_28_days
from app.cash_flow.cash_balance_forecast import forecast_next_30_days
from app.cash_flow.market_regime import get_market_regime_simplified
from app.cash_flow.orchestrator import determine_allocation_ratios
from app.cash_flow.market_report import (
    get_full_market_report, 
    collect_all_market_data, 
    generate_market_report,
    save_report_to_markdown
)

router = APIRouter()


@router.get("/query")
async def get_cashflow_query(query: str):
    # Split arguments properly for subprocess.run
    result = subprocess.run(
        ["python", "app/cash_flow/cash_flow_agent_bash.py", "--query", query],
        capture_output=True,
        text=True,
    )
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")

    if result.returncode != 0:
        raise HTTPException(
            status_code=500, detail=f"Agent execution failed: {result.stderr}"
        )

    return {"result": result.stdout}


@router.get("/ocbal")
async def get_opening_closing_balance():
    try:
        file_name = f"bank-data-raw.csv"
        file_path = os.path.join("app/cash_flow/streaming-bank-data", file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Data file not found: {file_name}"
            )

        df = pd.read_csv(file_path)

        # Get the latest date available in the dataset
        last_date = df["date"].max()

        # Filter data for the last date
        last_day_data = df[df["date"] == last_date]

        if last_day_data.empty:
            return {"opening_balance": 0, "closing_balance": 0, "date": last_date}

        # Get opening balance from the first record of the last date
        opening_balance = last_day_data.iloc[0]["opening_cash_balance"]

        # Get closing balance from the last record of the last date
        closing_balance = last_day_data.iloc[-1]["closing_cash_balance"]

        # RBI CRR Ratio (approx 4.5%)
        CRR_RATIO = 0.045
        liquidity_buffer = closing_balance * (1 - CRR_RATIO)

        return {
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "net-cash-flow": closing_balance - opening_balance,
            "liquidity_buffer": liquidity_buffer,
            "date": last_date,
        }
    except Exception as e:
        print(f"Error reading opening closing balance data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/liqregime")
async def get_liquidity_regime():
    try:
        result = predict_liquidity_regime()
        return result
    except Exception as e:
        print(f"Error reading liquidity regime data: {e}")


@router.get("/inandoutflow")
async def get_in_and_out_flow():
    try:
        result = analyze_last_28_days(
            file_path="app/cash_flow/streaming-bank-data/bank-data-raw.csv"
        )
        return result
    except Exception as e:
        print(f"Error reading in and out flow data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cashbalanceforecast")
async def get_cash_balance_forecast():
    try:
        result = forecast_next_30_days(
            models_dir="app/cash_flow/cash-flow-models",
            data_dir="app/cash_flow/streaming-bank-data",
            raw_data_file="app/cash_flow/streaming-bank-data/bank-data-raw.csv",
        )
        return {"result": result}

    except Exception as e:
        print(f"Error reading cashflow forecast =data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketregime")
async def get_market_regime():
    try:
        result = get_market_regime_simplified()
        return result
    except Exception as e:
        print(f"Error reading market regime data: {e}")


@router.get("/orchestrator")
async def get_orchestrator():
    try:
        result = determine_allocation_ratios()
        return result
    except Exception as e:
        print(f"Error reading orchestrator data: {e}")


@router.get("/io")
async def get_cashflow(number: str):
    try:
        # Construct file path
        file_name = f"dataset_H{number}_F{number}.csv"
        file_path = os.path.join("app/cash_flow/streaming-bank-data", file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Data file not found: {file_name}"
            )

        # Read CSV
        df = pd.read_csv(file_path)

        # Ensure we have the target column and rename it to 'net-cash-flow'
        if "target_next_window_cashflow" in df.columns:
            df = df.rename(columns={"target_next_window_cashflow": "net-cash-flow"})

        # Create a date column for convenience
        if all(
            col in df.columns
            for col in [
                "history_window_end_year",
                "history_window_end_month",
                "history_window_end_day",
            ]
        ):
            df["date"] = pd.to_datetime(
                dict(
                    year=df.history_window_end_year,
                    month=df.history_window_end_month,
                    day=df.history_window_end_day,
                )
            ).dt.strftime("%Y-%m-%d")

        # Return data (last 48 days only)
        return df.tail(48).to_dict(orient="records")

    except Exception as e:
        print(f"Error reading cashflow data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-report")
async def get_market_report():
    """
    Generate a comprehensive market report for bank treasurers.
    Calls all market tools and uses AI to generate actionable insights.
    Returns the report in Markdown format suitable for PDF conversion.
    """
    try:
        result = get_full_market_report(save_markdown=True)
        return {
            "status": "success",
            "timestamp": result["timestamp"],
            "report": result["report"],
            "markdown_path": result.get("markdown_path"),
            "errors": result["errors"]
        }
    except Exception as e:
        print(f"Error generating market report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-report/markdown")
async def get_market_report_markdown(download: bool = True):
    """
    Generate market report and return as Markdown.
    
    Args:
        download: If True, returns as downloadable .md file. 
                  If False (default), returns raw text.
    """
    try:
        # Don't save to disk, just generate the report
        result = get_full_market_report(save_markdown=False)
        markdown_content = result["report"]
        
        if download:
            # Return as downloadable file
            from datetime import datetime
            filename = f"market_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            return Response(
                content=markdown_content,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        else:
            # Return as plain text
            return PlainTextResponse(content=markdown_content)
    except Exception as e:
        print(f"Error generating market report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data")
async def get_raw_market_data():
    """
    Get raw market data from all tools without AI processing.
    Useful for custom analysis or debugging.
    """
    try:
        market_data = collect_all_market_data()
        return {
            "status": "success",
            "data": market_data
        }
    except Exception as e:
        print(f"Error collecting market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
