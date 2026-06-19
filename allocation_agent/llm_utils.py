import json
import os
import logging
from typing import Tuple, Optional
from dotenv import load_dotenv
from groq import Groq
from .schema import UserIntent, Constraints, MarketSignals, ConflictWarning

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Groq Client
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    logger.warning("GROQ_API_KEY not found in .env. LLM features will fail.")
    client = None
else:
    client = Groq(api_key=api_key)

MODEL = "llama-3.3-70b-versatile"

def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Helper to call Groq API with JSON mode.
    """
    if not client:
        raise ValueError("Groq Client not initialized. Check GROQ_API_KEY.")

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        raise

def analyze_intent_and_constraints(query: str) -> Tuple[UserIntent, Constraints]:
    """
    Uses LLM to analyze the query.
    Returns (UserIntent, Constraints).
    """
    logger.info("Calling LLM for Intent Analysis...")
    
    system_prompt = """
    You are a financial intent analyzer. Analyze the user's query and extract:
    1. Intent: "Conservative", "Balanced", or "Aggressive".
    2. Constraints: Specific limits mentioned (e.g., "max 40% stocks").
    
    Return JSON format:
    {
        "intent": "String",
        "constraints": {
            "max_stocks": float or null,
            "min_stocks": float or null,
            "max_bonds": float or null,
            "min_bonds": float or null,
            "max_cash": float or null,
            "min_cash": float or null
        }
    }
    Example: "I want aggressive growth but max 40% stocks, and keep 20% cash" -> {"intent": "Aggressive", "constraints": {"max_stocks": 0.4, "max_cash": 0.2}}
    """
    
    response_json = _call_llm(system_prompt, query)
    try:
        data = json.loads(response_json)
        intent = UserIntent(data.get("intent", "Balanced"))
        constraints = Constraints(**data.get("constraints", {}))
        return intent, constraints
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {response_json}")
        # Fallback
        return UserIntent.BALANCED, Constraints()

def check_conflict(intent: UserIntent, signals: MarketSignals) -> ConflictWarning:
    """
    Uses LLM to check for conflicts between User Intent and Market Signals.
    """
    logger.info("Calling LLM for Conflict Detection...")
    
    system_prompt = """
    You are a financial risk manager. Compare the User's Intent with the Current Market Signals.
    Detect if there is a dangerous conflict (e.g., User wants "Aggressive" but Market is "Bearish" or "High Volatility").
    
    Return JSON format:
    {
        "detected": boolean,
        "message": "String explanation or empty string"
    }
    """
    
    user_prompt = f"""
    User Intent: {intent.value}
    Market Signals:
    - Sentiment: {signals.sentiment.value}
    - Volatility: {signals.volatility.value}
    - Liquidity Risk: {signals.liquidity_risk.value}
    - Yield Trend: {signals.yield_trend.value}
    """
    
    response_json = _call_llm(system_prompt, user_prompt)
    try:
        data = json.loads(response_json)
        return ConflictWarning(
            detected=data.get("detected", False),
            message=data.get("message", "")
        )
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {response_json}")
        return ConflictWarning(detected=False, message="")
