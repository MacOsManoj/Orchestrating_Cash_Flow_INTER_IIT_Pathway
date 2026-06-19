"""
Bond Pipeline Test Script
==========================

Tests all components of the bond pipeline to verify connections and functionality.

Run with:
    python test_pipeline.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "agents"))
sys.path.insert(0, str(Path(__file__).parent / "integration"))

# Load environment
from dotenv import load_dotenv

load_dotenv()


# Colors for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")


def print_success(msg: str):
    print(f"{Colors.GREEN} {msg}{Colors.END}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW} {msg}{Colors.END}")


def print_info(msg: str):
    print(f"{Colors.BLUE} {msg}{Colors.END}")


def test_imports():
    """Test all required imports."""
    print_header("Testing Imports")

    results = {}

    # Core dependencies
    core_imports = [
        ("langchain_openai", "LangChain OpenAI"),
        ("langchain_core", "LangChain Core"),
        ("langgraph", "LangGraph"),
        ("pydantic", "Pydantic"),
        ("numpy", "NumPy"),
        ("scipy", "SciPy"),
    ]

    for module, name in core_imports:
        try:
            __import__(module)
            print_success(f"{name} imported successfully")
            results[name] = True
        except ImportError as e:
            print_error(f"{name} import failed: {e}")
            results[name] = False

    # Agent imports
    print_info("\nTesting agent imports...")

    agent_imports = [
        ("portfolio_manager", "Portfolio Manager Agent"),
        ("analyst", "Analyst Agent"),
        ("advisory_agent", "Advisory Agent"),
        ("orchestrator", "Orchestrator"),
    ]

    for module, name in agent_imports:
        try:
            __import__(module)
            print_success(f"{name} imported successfully")
            results[name] = True
        except ImportError as e:
            print_error(f"{name} import failed: {e}")
            results[name] = False
        except Exception as e:
            print_warning(f"{name} import warning: {e}")
            results[name] = "warning"

    return results


def test_environment():
    """Test environment configuration."""
    print_header("Testing Environment")

    results = {}

    # Check OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print_success(f"OPENAI_API_KEY found (ends with ...{api_key[-4:]})")
        results["OPENAI_API_KEY"] = True
    else:
        print_error("OPENAI_API_KEY not found")
        results["OPENAI_API_KEY"] = False

    # Check directories
    dirs_to_check = [
        "agents",
        "integration",
        "files-for-indexing",
        "files-for-indexing/cache",
    ]

    for dir_name in dirs_to_check:
        dir_path = Path(__file__).parent / dir_name
        if dir_path.exists():
            print_success(f"Directory exists: {dir_name}")
            results[f"dir_{dir_name}"] = True
        else:
            print_warning(f"Directory missing: {dir_name}")
            # Try to create it
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print_info(f"  Created: {dir_name}")
                results[f"dir_{dir_name}"] = True
            except Exception as e:
                print_error(f"  Could not create: {e}")
                results[f"dir_{dir_name}"] = False

    return results


def test_llm_connection():
    """Test LLM connection."""
    print_header("Testing LLM Connection")

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o", temperature=0, max_tokens=50)

        response = llm.invoke("Say 'Bond Pipeline Connected' in exactly 3 words.")
        print_success(f"LLM Response: {response.content}")
        return True

    except Exception as e:
        print_error(f"LLM connection failed: {e}")
        return False


def test_bond_calculator():
    """Test bond calculator functionality."""
    print_header("Testing Bond Calculator")

    try:
        from analyst import BondCalculator

        calc = BondCalculator()

        # Test YTM calculation
        ytm = calc.calculate_ytm(
            price=98.0,
            face_value=100.0,
            coupon_rate=7.0,
            years_to_maturity=5.0,
            frequency=2,
        )
        print_success(f"YTM Calculation: {ytm:.4f}%")

        # Test duration calculation
        mac_duration = calc.calculate_macaulay_duration(
            ytm=7.5, coupon_rate=7.0, years_to_maturity=5.0, frequency=2
        )
        print_success(f"Macaulay Duration: {mac_duration:.4f} years")

        # Test modified duration
        mod_duration = calc.calculate_modified_duration(
            macaulay_duration=mac_duration, ytm=7.5, frequency=2
        )
        print_success(f"Modified Duration: {mod_duration:.4f} years")

        # Test convexity
        convexity = calc.calculate_convexity(
            ytm=7.5, coupon_rate=7.0, years_to_maturity=5.0, frequency=2
        )
        print_success(f"Convexity: {convexity:.4f}")

        return True

    except Exception as e:
        print_error(f"Bond calculator test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_analyst_agent():
    """Test analyst agent."""
    print_header("Testing Analyst Agent")

    try:
        from analyst import (
            AnalystAgent,
            BondFeatures,
            ModelPrediction,
            RateForecast,
            create_analyst_agent,
        )

        # Create sample data
        sample_bond = BondFeatures(
            bond_id="TEST001",
            bond_name="Test Bond 7.5% 2030",
            issuer="Test Issuer",
            face_value=100,
            coupon_rate=7.5,
            coupon_frequency=2,
            maturity_date="2030-01-01",
            current_price=99.5,
            credit_rating="AAA",
            is_government=False,
        )

        sample_prediction = ModelPrediction(
            bond_id="TEST001",
            bond_name="Test Bond 7.5% 2030",
            issuer="Test Issuer",
            current_price=99.5,
            current_ytm=7.6,
            predicted_price=100.5,
            model_confidence=0.75,
        )

        sample_forecast = RateForecast(
            forecast_date=datetime.now().strftime("%Y-%m-%d"),
            repo_rate=6.5,
            yield_1y=6.8,
            yield_5y=7.0,
            yield_10y=7.2,
        )

        print_info("Creating Analyst Agent...")
        agent = create_analyst_agent()
        print_success("Analyst Agent created successfully")

        print_info("Running analysis (this may take a moment)...")
        result = agent.analyze(
            bank_id="TEST_BANK",
            bond_features=[sample_bond],
            model_predictions=[sample_prediction],
            rate_forecast=sample_forecast,
        )

        if result.get("error"):
            print_error(f"Analysis error: {result['error']}")
            return False

        analytics = result.get("bond_analytics", [])
        if analytics:
            bond = analytics[0]
            print_success(f"Bond analyzed: {bond.bond_name}")
            print_info(f"  YTM: {bond.yield_to_maturity:.2f}%")
            print_info(f"  Duration: {bond.modified_duration:.2f} years")
            print_info(f"  Risk Score: {bond.risk_adjusted_score:.1f}")
        else:
            print_warning("No analytics returned")

        return True

    except Exception as e:
        print_error(f"Analyst agent test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_advisory_agent():
    """Test advisory agent."""
    print_header("Testing Advisory Agent")

    try:
        from advisory_agent import AdvisoryAgent, create_advisory_agent

        # Sample analyst output
        sample_analyst_output = {
            "ranked_bonds": [
                {
                    "bond_id": "TEST001",
                    "bond_name": "Test Bond 7.5% 2030",
                    "issuer": "Test Issuer",
                    "credit_rating": "AAA",
                    "yield_to_maturity": 7.6,
                    "modified_duration": 4.2,
                    "total_expected_return": 0.8,
                    "liquidity_score": 0.7,
                    "model_confidence": 0.75,
                    "risk_adjusted_score": 72,
                }
            ],
            "macro": {"rate_outlook": "Stable", "duration_stance": "neutral"},
        }

        print_info("Creating Advisory Agent...")
        agent = create_advisory_agent()
        print_success("Advisory Agent created successfully")

        print_info("Generating advisory (this may take a moment)...")
        result = agent.generate_advisory(
            bank_id="TEST_BANK",
            analyst_output=sample_analyst_output,
            user_context={
                "bank_id": "TEST_BANK",
                "bank_name": "Test Bank",
                "risk_appetite": "moderate",
                "current_duration": 4.0,
                "current_yield": 7.0,
                "available_cash_cr": 50.0,
                "total_aum_cr": 500.0,
            },
        )

        if result.get("error"):
            print_error(f"Advisory error: {result['error']}")
            return False

        recommendations = result.get("recommendations", [])
        if recommendations:
            print_success(f"Generated {len(recommendations)} recommendations")
            for rec in recommendations[:2]:
                print_info(
                    f"  {rec.get('action', 'N/A').upper()} - {rec.get('bond_name', 'Unknown')}"
                )
        else:
            print_warning("No recommendations generated")

        return True

    except Exception as e:
        print_error(f"Advisory agent test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_orchestrator():
    """Test orchestrator."""
    print_header("Testing Orchestrator")

    try:
        from orchestrator import BondOrchestrator, create_orchestrator

        print_info("Creating Orchestrator...")
        orchestrator = create_orchestrator()
        print_success("Orchestrator created successfully")

        # Test simple query
        print_info("Testing simple query: 'Hello'")
        response = orchestrator.chat("Hello", "TEST_BANK")

        if response:
            print_success(f"Intent: {response.intent.value}")
            print_success(f"Confidence: {response.confidence:.2f}")
            print_info(f"Response preview: {response.response_text[:100]}...")
        else:
            print_error("No response from orchestrator")
            return False

        # Test help query
        print_info("\nTesting help query: 'help'")
        response = orchestrator.chat("help", "TEST_BANK")

        if response:
            print_success(f"Intent: {response.intent.value}")
            print_info(f"Response preview: {response.response_text[:100]}...")

        return True

    except Exception as e:
        print_error(f"Orchestrator test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_integration_layer():
    """Test integration layer."""
    print_header("Testing Integration Layer")

    results = {}

    # Test each integration module
    integration_modules = [
        ("portfolio_int", "Portfolio Integration"),
        ("analyst_int", "Analyst Integration"),
        ("advisory_int", "Advisory Integration"),
        ("data_loader", "Data Loader"),
    ]

    for module, name in integration_modules:
        try:
            # Try to import from integration folder
            sys.path.insert(0, str(Path(__file__).parent / "integration"))
            imported = __import__(module)
            print_success(f"{name} imported successfully")
            results[name] = True
        except ImportError as e:
            print_warning(f"{name} not found: {e}")
            results[name] = False
        except Exception as e:
            print_error(f"{name} error: {e}")
            results[name] = False

    return results


def test_data_sources():
    """Test mock data sources."""
    print_header("Testing Data Sources")

    results = {}

    try:
        from data_loader import get_data_loader

        loader = get_data_loader()

        # Test RBI MPR data
        mpr = loader.get_rbi_mpr_data()
        if mpr and mpr.get("policy_repo_rate"):
            print_success(f"RBI MPR: Repo rate = {mpr.get('policy_repo_rate')}%")
            results["rbi_mpr"] = True
        else:
            print_warning("RBI MPR data not found or incomplete")
            results["rbi_mpr"] = False

        # Test NSE Bond data
        nse = loader.get_nse_bond_data()
        if nse and nse.get("gsec_prices"):
            print_success(
                f"NSE Bonds: {len(nse.get('gsec_prices', []))} G-Secs, {len(nse.get('corporate_bonds', []))} corporates"
            )
            results["nse_bonds"] = True
        else:
            print_warning("NSE Bond data not found or incomplete")
            results["nse_bonds"] = False

        # Test News sentiment
        news = loader.get_news_sentiment()
        if news and news.get("news_items"):
            print_success(
                f"News: {len(news.get('news_items', []))} items, sentiment={news.get('aggregated_sentiment', {}).get('overall', 'N/A')}"
            )
            results["news"] = True
        else:
            print_warning("News data not found or incomplete")
            results["news"] = False

        # Test ML model output
        ml = loader.get_ml_model_output()
        if ml and ml.get("forecast"):
            print_success(
                f"ML Model: 10Y forecast = {ml.get('forecast', {}).get('10Y_forecast', {}).get('point_estimate', 'N/A')}%"
            )
            results["ml_model"] = True
        else:
            print_warning("ML model data not found or incomplete")
            results["ml_model"] = False

        # Test Portfolio data
        banks = loader.list_banks()
        if banks:
            print_success(f"Portfolios: {len(banks)} banks - {', '.join(banks[:3])}")
            results["portfolios"] = True
        else:
            print_warning("No bank portfolios found")
            results["portfolios"] = False

        return results

    except Exception as e:
        print_error(f"Data sources test failed: {e}")
        import traceback

        traceback.print_exc()
        return {"data_loader": False}


def run_all_tests():
    """Run all tests."""
    print(f"\n{Colors.BOLD}Bond Pipeline Test Suite{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_results = {}

    # 1. Test imports
    import_results = test_imports()
    all_results["imports"] = all(v for v in import_results.values() if v is not False)

    # 2. Test environment
    env_results = test_environment()
    all_results["environment"] = all(v for v in env_results.values())

    # 3. Test data sources
    data_results = test_data_sources()
    all_results["data_sources"] = all(v for v in data_results.values())

    # 4. Test LLM connection
    if env_results.get("OPENAI_API_KEY"):
        all_results["llm"] = test_llm_connection()
    else:
        print_warning("\nSkipping LLM test (no API key)")
        all_results["llm"] = False

    # 5. Test bond calculator
    all_results["calculator"] = test_bond_calculator()

    # 6. Test analyst agent
    if all_results["llm"]:
        all_results["analyst"] = test_analyst_agent()
    else:
        print_warning("\nSkipping Analyst Agent test (LLM not connected)")
        all_results["analyst"] = False

    # 7. Test advisory agent
    if all_results["analyst"]:
        all_results["advisory"] = test_advisory_agent()
    else:
        print_warning("\nSkipping Advisory Agent test (Analyst not working)")
        all_results["advisory"] = False

    # 8. Test orchestrator
    if all_results["llm"]:
        all_results["orchestrator"] = test_orchestrator()
    else:
        print_warning("\nSkipping Orchestrator test (LLM not connected)")
        all_results["orchestrator"] = False

    # 9. Test integration layer
    int_results = test_integration_layer()
    all_results["integration"] = all(v for v in int_results.values())

    # Summary
    print_header("Test Summary")

    passed = sum(1 for v in all_results.values() if v)
    total = len(all_results)

    for test_name, passed_test in all_results.items():
        if passed_test:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")

    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print(
            f"\n{Colors.GREEN}{Colors.BOLD} All tests passed! Pipeline is ready.{Colors.END}"
        )
        print(f"\n{Colors.BLUE}To run the app:{Colors.END}")
        print(f"  cd bond-pipeline")
        print(f"  streamlit run app.py")
    else:
        print(
            f"\n{Colors.YELLOW}Some tests failed. Check the errors above.{Colors.END}"
        )

    return all_results


if __name__ == "__main__":
    run_all_tests()
