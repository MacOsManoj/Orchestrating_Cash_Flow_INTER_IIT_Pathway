# Agent Test Suite

Comprehensive test suite for all agents in the bond pipeline using mock data from `files-mock` directory.

## Test Files

- `test_agents_comprehensive.py` - Main test suite with tests for all agents
- `run_tests.py` - Test runner script

## Running Tests

### Run All Tests

```bash
cd bond-pipeline
python tests/run_tests.py
```

Or using unittest directly:

```bash
cd bond-pipeline
python -m unittest tests.test_agents_comprehensive
```

### Run Specific Test Classes

```bash
# Test ML Model Agent only
python -m unittest tests.test_agents_comprehensive.TestMLModelAgent

# Test Analyst Agent only
python -m unittest tests.test_agents_comprehensive.TestAnalystAgent

# Test Pipeline Integration
python -m unittest tests.test_agents_comprehensive.TestPipelineIntegration
```

### Run with Verbose Output

```bash
python -m unittest tests.test_agents_comprehensive -v
```

## Test Coverage

The test suite covers:

1. **ML Model Agent** (`TestMLModelAgent`)
   - Agent creation
   - Loading mock data
   - Batch prediction
   - Prediction with yield curve

2. **Query Classifier Agent** (`TestQueryClassifierAgent`)
   - Query classification
   - Keyword-based fallback
   - Entity extraction

3. **Analyst Agent** (`TestAnalystAgent`)
   - Bond analysis with mock data
   - Filtering by criteria
   - Identifying rate sensitive bonds

4. **Scoring Agent** (`TestScoringAgent`)
   - Scoring bonds
   - Getting top bonds
   - Categorizing bonds

5. **Advisory Agent** (`TestAdvisoryAgent`)
   - Generating advisory recommendations
   - Increase yield strategy
   - Portfolio impact calculation

6. **Explainability Agent** (`TestExplainabilityAgent`)
   - Explaining recommendations
   - SHAP value calculation

7. **Planner Agent** (`TestPlannerAgent`)
   - Creating execution plans
   - Plan structure validation

8. **Portfolio Manager** (`TestPortfolioManager`)
   - Portfolio node execution
   - Constraint checking

9. **Pipeline Integration** (`TestPipelineIntegration`)
   - End-to-end flow
   - All agents working together

## Mock Data

Tests use mock data from `files-mock/` directory:

- `analytics/ml_model_output.json` - ML model predictions
- `analytics/nse_bond_data.json` - NSE bond market data
- `analytics/rbi_mpr_data.json` - RBI monetary policy data
- `analytics/news_sentiment.json` - News sentiment data
- `analytics/analyst_output.json` - Sample analyst outputs
- `portfolios/SAMPLE_BANK_001.json` - Sample portfolio data

## Requirements

- Python 3.8+
- All dependencies from `requirements.txt`
- OpenAI API key (optional, for LLM-based agents - tests use mocks when not available)

## Notes

- Some tests use mocked LLM responses to avoid API calls
- Tests are designed to work with mock data structure
- Real API keys are not required for most tests (LLM agents are mocked)
- The test suite validates both individual agent functionality and pipeline integration

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running from the `bond-pipeline` directory:

```bash
cd bond-pipeline
python tests/run_tests.py
```

### Mock Data Not Found

Ensure the `files-mock` directory exists and contains the required JSON files. The tests will fail gracefully with warnings if mock data is missing.

### LLM Tests Failing

LLM-based agents (Query Classifier, Advisory, Explainability, Planner) use mocked responses by default. If you want to test with real LLM calls, set `OPENAI_API_KEY` environment variable and the tests will use real API calls (may incur costs).

