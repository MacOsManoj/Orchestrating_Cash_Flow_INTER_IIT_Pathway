# Orchestrator V3 - LangGraph-Based Intelligent Pipeline

## Overview

Orchestrator V3 is a complete rewrite of the bond trading orchestrator using **LangGraph** for intelligent, dynamic routing and conditional execution. Unlike the naive sequential execution in V2, V3 uses a state graph with conditional edges to make intelligent decisions about which agents to run based on query classification and results.

## Key Improvements Over V2

### 1. **Intelligent Routing**
- Uses LangGraph StateGraph for dynamic flow control
- Conditional edges based on query classification
- Skips unnecessary agents when not needed
- Parallel tool execution where possible

### 2. **Query-Aware Execution**
- Automatically detects if portfolio access is needed
- Conditionally runs explainability only when requested
- Smart RAG retrieval based on query content
- Adapts execution path based on query type

### 3. **Better Error Handling**
- Errors are tracked in state
- Execution continues even if some agents fail
- Detailed execution path logging

### 4. **State Management**
- Centralized state management via GraphState
- Clear separation between graph state and output state
- Tracks execution path for debugging

## Architecture

```
┌─────────────┐
│ Validate    │
│ Query       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Classify    │
│ Query       │
└──────┬──────┘
       │
       ├───[Needs Portfolio?]───► Check Portfolio
       │
       ▼
┌─────────────┐
│ Plan        │
│ Execution            │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Execute     │
│ Tools       │
│ (Parallel)  │
└──────┬──────┘
       │
       ├───[Needs ML?]───► ML Model
       │
       ▼
┌─────────────┐
│ Analyst     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Scoring     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Advisory    │
└──────┬──────┘
       │
       ├───[Needs Explain?]───► Explainability
       │
       ▼
┌─────────────┐
│ Finalize    │
└──────┬──────┘
       │
       ▼
      END
```

## Execution Flow

### 1. **Validate Query**
- Checks if query is bond-related
- Early exit if not relevant

### 2. **Classify Query**
- Uses QueryClassifier agent
- Determines:
  - Needs portfolio access?
  - Needs explainability?
  - Needs RAG retrieval?

### 3. **Check Portfolio** (Conditional)
- Only runs if `needs_portfolio` is True
- Loads user portfolio if exists

### 4. **Plan Execution**
- Uses Planner agent to create execution plan
- Overrides plan flags based on classification

### 5. **Execute Tools** (Parallel)
- Runs all required tools in parallel
- Updates state with results
- Tracks cache hits

### 6. **Run ML Model** (Conditional)
- Only runs if in execution plan
- Uses yield forecasts and news if available

### 7. **Run Analyst**
- Always runs (required for recommendations)
- Uses ML predictions and credit data

### 8. **Run Scoring**
- Scores all bonds
- Ranks by total score

### 9. **Run Advisory**
- Generates recommendations
- Uses classified query, analytics, scores, portfolio

### 10. **Run Explainability** (Conditional)
- Only runs if:
  - User explicitly asks ("explain", "why", etc.)
  - Plan has `needs_explainability=True`

### 11. **Finalize**
- Converts GraphState to EnhancedAgentState
- Calculates processing time
- Logs execution path

## Conditional Routing Logic

### Portfolio Check
```python
def _should_check_portfolio(state: GraphState) -> str:
    return "yes" if state.get("needs_portfolio", False) else "no"
```

Triggers when:
- Query type is PORTFOLIO
- Intent is REDUCE_DURATION
- Query contains "portfolio", "my bonds", "holdings"

### ML Model
```python
def _should_run_ml(state: GraphState) -> str:
    plan = state.get("execution_plan")
    return "yes" if plan and AgentType.ML_MODEL in plan.agents_needed else "no"
```

### Explainability
```python
def _should_explain(state: GraphState) -> str:
    plan = state.get("execution_plan")
    needs_explain = state.get("needs_explainability", False)
    has_advisory = state.get("advisory") is not None
    
    if plan and plan.needs_explainability:
        return "yes"
    if needs_explain and has_advisory:
        return "yes"
    return "no"
```

## Usage

```python
from orchestrator_v3 import create_orchestrator_v3
from schemas_v2 import SystemConfigV2

# Initialize
config = SystemConfigV2(
    openai_api_key="sk-...",
    llm_model="gpt-4o-mini"
)
orchestrator = create_orchestrator_v3(config)

# Run query
state = await orchestrator.run_async(
    query="Find high yield AAA bonds",
    user_id="user123"
)

# Access results
print(state.advisory.recommendations)
print(state.execution_plan.reasoning)
print(state.execution_path)  # Shows which nodes executed
```

## State Structure

### GraphState (Internal)
- All execution state
- Tracks current step
- Execution path
- Errors

### EnhancedAgentState (Output)
- Clean output format
- Compatible with existing code
- All results and metadata

## Benefits

1. **Performance**: Skips unnecessary agents
2. **Intelligence**: Adapts to query type
3. **Maintainability**: Clear state transitions
4. **Debuggability**: Execution path tracking
5. **Extensibility**: Easy to add new nodes/edges

## Migration from V2

The API is identical, so migration is simple:

```python
# Old
from orchestrator_v2 import create_orchestrator_v2
orchestrator = create_orchestrator_v2(config)

# New
from orchestrator_v3 import create_orchestrator_v3
orchestrator = create_orchestrator_v3(config)
```

The `run_async` method signature is unchanged, so existing code works without modification.

## Future Enhancements

1. **Retry Logic**: Automatic retry for failed agents
2. **Caching**: Cache intermediate results
3. **Streaming**: Stream results as they're generated
4. **Monitoring**: Add observability hooks
5. **A/B Testing**: Test different execution strategies

