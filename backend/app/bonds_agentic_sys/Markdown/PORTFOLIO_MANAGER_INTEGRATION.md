# Portfolio Manager Integration Guide

## Overview

The MongoDB Portfolio Manager is automatically integrated into the orchestrator pipeline and runs **automatically** when needed. Here's how it works:

## When Does It Start Running?

The Portfolio Manager runs in **two places** in the pipeline:

### 1. **Automatic Portfolio Check** (Always for Bond Queries)
```
User Query → Validate → Classify → Gather Real-time Info → **Check Portfolio** → Plan → ...
```

**Location**: `_check_portfolio()` node in orchestrator_v3.py (line 769)

**When**: 
- Runs for **all bond-related queries** after classification
- Happens **automatically** - no manual trigger needed
- Executes **before** planning to know if user has a portfolio

**Code Flow**:
```python
async def _check_portfolio(self, state: GraphState) -> GraphState:
    # Automatically called for bond queries
    result = await self.tools[ToolType.PORTFOLIO_MANAGER].get_portfolio(
        state["user_id"]  # Uses user_id from query
    )
    if result.success:
        state["portfolio"] = result.data  # Portfolio stored in state
```

### 2. **Planner-Requested Portfolio Access** (Conditional)
```
Plan Execution → Execute Tools (Parallel) → **Portfolio Manager Tool** → ...
```

**Location**: `_execute_tools()` node in orchestrator_v3.py (line 935)

**When**:
- Only if the **Planner Agent** decides portfolio is needed
- Runs in **parallel** with other tools (news, web search, etc.)
- Planner decides based on query intent (e.g., "my portfolio", "my holdings")

**Code Flow**:
```python
async def _execute_tools(self, state: GraphState) -> GraphState:
    for tool_call in plan.tools_needed:
        if tool_type == ToolType.PORTFOLIO_MANAGER:
            # Runs in parallel with other tools
            tasks.append(
                self.tools[tool_type].get_portfolio(state["user_id"])
            )
```

## Complete Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY RECEIVED                        │
│              "What bonds should I buy?"                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. VALIDATE QUERY                                            │
│    - Check guardrails                                        │
│    - Validate input                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CLASSIFY QUERY                                            │
│    - QueryClassifier Agent                                   │
│    - Determines: needs_portfolio = True/False                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. GATHER REAL-TIME INFO                                     │
│    - Web search + News (parallel)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. CHECK PORTFOLIO ⭐ FIRST RUN                              │
│    ┌──────────────────────────────────────┐                 │
│    │ PortfolioManagerTool.get_portfolio() │                 │
│    │   ↓                                   │                 │
│    │ PortfolioManager.get_portfolio()     │                 │
│    │   ↓                                   │                 │
│    │ MongoDB Query:                       │                 │
│    │   db.portfolios.find({                │                 │
│    │     $or: [                            │                 │
│    │       {user_id: "SAMPLE_USER_001"},   │                 │
│    │       {portfolio_id: "..."}          │                 │
│    │     ]                                 │                 │
│    │   })                                  │                 │
│    └──────────────────────────────────────┘                 │
│    ✅ Portfolio found → state["portfolio"] = Portfolio      │
│    ❌ Not found → state["portfolio"] = None                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. PLAN EXECUTION                                            │
│    - Planner Agent                                          │
│    - Uses portfolio info to decide tools needed             │
│    - May add PORTFOLIO_MANAGER to tools_needed              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. EXECUTE TOOLS (Parallel) ⭐ SECOND RUN (if needed)        │
│    ┌──────────┬──────────┬──────────┬──────────┐           │
│    │ News     │ Web      │ CRISIL   │ Portfolio│           │
│    │ Scraper  │ Search   │ Scraper  │ Manager  │           │
│    └──────────┴──────────┴──────────┴──────────┘           │
│                                                              │
│    Portfolio Manager runs here if Planner requested it     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. RUN ML MODEL → ANALYST → SCORING                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. RUN RESPONSE/ADVISORY AGENT                               │
│    - Uses state["portfolio"] for recommendations            │
│    - Validates trades against portfolio constraints          │
│    - PortfolioManager.validate_recommendations()             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. FINALIZE & RETURN                                         │
└──────────────────────────────────────────────────────────────┘
```

## How Agents Use Portfolio Data

### 1. **Response/Advisory Agent** (Primary User)
```python
# In orchestrator_v3.py, _run_response()
state["advisory"] = self.response_agent.generate_response(
    classified_query=classified,
    bond_analytics=state.get("bond_analytics", {}),
    bond_scores=state.get("bond_scores", {}),
    portfolio=portfolio_to_pass,  # ← Portfolio from MongoDB
    # ... other params
)
```

**What it does**:
- Generates personalized recommendations based on user's portfolio
- Checks current holdings
- Suggests trades that align with portfolio goals
- Validates recommendations against portfolio constraints

### 2. **Portfolio Manager Validation**
```python
# In portfolio_manager.py
def validate_recommendations(
    self, 
    portfolio: Portfolio,  # ← From MongoDB
    recommendations: List[TradeRecommendation],
    # ...
) -> List[TradeRecommendation]:
    # Validates:
    # - Cash availability for BUY
    # - Position exists for SELL
    # - Risk profile alignment
    # - Sector concentration limits
    # - Position size limits
```

## MongoDB Connection Lifecycle

### Initialization (When Orchestrator Starts)
```python
# orchestrator_v3.py __init__()
self.tools = {
    ToolType.PORTFOLIO_MANAGER: create_portfolio_manager(
        config.portfolio_db_path,
        use_mongodb=True  # ← MongoDB enabled by default
    ),
}
```

**What happens**:
1. `PortfolioManagerTool` is created
2. `PortfolioManager` is created with `use_mongodb=True`
3. MongoDB client connects (singleton pattern)
4. Connection tested (with fallback to files if fails)

### Runtime (During Query Processing)
```python
# When get_portfolio() is called:
1. PortfolioManager.get_portfolio(user_id)
   ↓
2. Check: use_mongodb and mongodb_collection is not None?
   ↓
3. Query MongoDB:
   collection.find_one({
       "$or": [
           {"user_id": user_id},
           {"portfolio_id": user_id},
           {"bank_id": user_id}
       ]
   })
   ↓
4. Convert MongoDB document → Portfolio object
   ↓
5. Return Portfolio (or None if not found)
```

## Example: Complete Query Flow

### Query: "What bonds should I buy for my portfolio?"

```
1. User sends query with user_id="SAMPLE_USER_001"
   ↓
2. Orchestrator runs pipeline
   ↓
3. _check_portfolio() runs automatically
   ↓
4. MongoDB query executes:
   db.portfolios.find({user_id: "SAMPLE_USER_001"})
   ↓
5. Portfolio retrieved:
   {
     portfolio_id: "PF_001",
     total_value: 201500.00,
     cash: 25000.00,
     positions: [...]
   }
   ↓
6. Portfolio stored in state["portfolio"]
   ↓
7. Planner uses portfolio info to plan
   ↓
8. Advisory Agent generates recommendations:
   - Checks current holdings
   - Validates cash availability
   - Suggests bonds that fit portfolio
   ↓
9. PortfolioManager.validate_recommendations():
   - Checks if BUY recommendations have enough cash
   - Validates position size limits
   - Checks risk profile alignment
   ↓
10. Final recommendations returned to user
```

## Key Points

1. **Automatic**: Portfolio Manager runs automatically - no manual setup needed
2. **Transparent**: MongoDB is used under the hood - agents don't need to know
3. **Fallback**: If MongoDB fails, automatically falls back to file-based storage
4. **State-based**: Portfolio is stored in pipeline state, available to all agents
5. **Parallel**: Can run in parallel with other tools for efficiency
6. **Validation**: Portfolio Manager validates all trade recommendations

## Testing the Integration

### Test 1: Query with Portfolio
```python
from orchestrator_v3 import create_orchestrator_v3
from schemas_v2 import SystemConfigV2

config = SystemConfigV2(...)
orchestrator = create_orchestrator_v3(config)

result = await orchestrator.run_async(
    query="What bonds should I buy?",
    user_id="SAMPLE_USER_001"  # ← Portfolio will be loaded from MongoDB
)

# Portfolio is automatically loaded and used
print(result.portfolio)  # Portfolio object
print(result.advisory.recommendations)  # Recommendations based on portfolio
```

### Test 2: Query without Portfolio
```python
result = await orchestrator.run_async(
    query="What are the best bonds?",
    user_id="NEW_USER_123"  # ← No portfolio in MongoDB
)

# Pipeline still works, just without portfolio context
print(result.portfolio)  # None
```

## Monitoring

To see when Portfolio Manager runs, check the logs:

```
🔍 CHECKING PORTFOLIO...
✓ Portfolio found: ₹201,500.00

# Or in tool execution:
📊 EXECUTING TOOLS...
  Executing 3 tools in parallel...
✓ Tools completed (Cache hits: 0/3)
```

## Summary

- **When**: Automatically runs for all bond queries (step 4) and optionally during tool execution (step 6)
- **How**: MongoDB queries executed transparently via PortfolioManager
- **Where**: Portfolio data stored in pipeline state, accessible to all agents
- **Why**: Enables personalized recommendations and trade validation
- **Fallback**: Automatically uses file-based storage if MongoDB unavailable

The integration is **seamless** - you just use the orchestrator normally, and MongoDB Portfolio Manager handles everything automatically!

