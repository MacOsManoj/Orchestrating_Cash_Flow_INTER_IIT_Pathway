# End-to-End Pipeline Test

Comprehensive end-to-end test that runs the complete pipeline from user query to recommendations.

## Running the E2E Test

```bash
cd bond-pipeline
python tests/test_pipeline_e2e.py
```

## What It Tests

The E2E test validates the complete pipeline flow:

1. **Simple Query Test** - Basic buy recommendation query
   - Tests: Planner → Query Classifier → ML Model → Analyst → Scoring → Advisory
   - Verifies all agents execute in sequence
   - Checks final recommendations are generated

2. **Portfolio Query Test** - Query with portfolio context
   - Tests portfolio loading and integration
   - Verifies portfolio-aware recommendations
   - Checks portfolio impact calculations

3. **Explanation Query Test** - Query that triggers explainability
   - Tests conditional explainability agent
   - Verifies explanations are generated when requested
   - Checks SHAP-like attribution

4. **Strategy Query Test** - Specific strategy (duration reduction)
   - Tests intent detection and strategy routing
   - Verifies strategy-specific recommendations
   - Checks tool integration (portfolio manager)

## Test Results

The test provides detailed output showing:
- Execution plan creation
- Tool execution (with cache hits)
- Agent execution sequence
- Final recommendations
- Processing times
- Summary statistics

## Requirements

- OpenAI API key (set `OPENAI_API_KEY` environment variable)
- Mock data in `files-mock/` directory
- All dependencies installed

## Expected Output

```
✓ Execution Plan Created
✓ Query Classified
✓ ML Predictions generated
✓ Bond Analytics created
✓ Bond Scores calculated
✓ Advisory Output with recommendations
✓ Processing completed successfully
```

## Notes

- Uses `gpt-4o-mini` model for cost efficiency
- RAG is disabled for faster testing
- All agents use mock data from `files-mock/`
- Tests verify the complete flow works end-to-end

