"""
Utils package
"""

from .model_selector import ModelSelector, AgentType, ModelTier, create_model_selector

# Import utility functions from parent utils.py file
import sys
import os
import importlib.util

# Get the parent directory (bond-pipeline)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
utils_py_path = os.path.join(parent_dir, "utils.py")

# Import from utils.py (the file, not the package) using importlib
try:
    spec = importlib.util.spec_from_file_location("utils_module", utils_py_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)

    # Import the functions we need
    calculate_duration = utils_module.calculate_duration
    calculate_convexity = utils_module.calculate_convexity
    price_bond = utils_module.price_bond
    years_to_maturity = utils_module.years_to_maturity
    interpolate_yield = utils_module.interpolate_yield
    calculate_liquidity_score = utils_module.calculate_liquidity_score
    calculate_rate_sensitivity = utils_module.calculate_rate_sensitivity
    optimal_barbell_weights = utils_module.optimal_barbell_weights
    classify_duration_bucket = utils_module.classify_duration_bucket
except (ImportError, FileNotFoundError, AttributeError) as e:
    # If utils.py is not found or functions don't exist, these will be None
    print(f"Warning: Could not import from utils.py: {e}")
    calculate_duration = None
    calculate_convexity = None
    price_bond = None
    years_to_maturity = None
    interpolate_yield = None
    calculate_liquidity_score = None
    calculate_rate_sensitivity = None
    optimal_barbell_weights = None
    classify_duration_bucket = None

# Import context manager
try:
    from .context_manager import ContextManager, create_context_manager
except ImportError:
    ContextManager = None
    create_context_manager = None

__all__ = [
    "ModelSelector",
    "AgentType",
    "ModelTier",
    "create_model_selector",
    "ContextManager",
    "create_context_manager",
    "calculate_duration",
    "calculate_convexity",
    "price_bond",
    "years_to_maturity",
    "interpolate_yield",
    "calculate_liquidity_score",
    "calculate_rate_sensitivity",
    "optimal_barbell_weights",
    "classify_duration_bucket",
]
