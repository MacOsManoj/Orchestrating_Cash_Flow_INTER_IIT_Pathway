# Architecture Comparison: Diagram vs Current Implementation

## Overview
This document compares the architecture diagram with the current pipeline implementation and identifies gaps.

## Architecture Diagram Components

### ✅ **Implemented Components**

1. **UI → Query Classifier → Orchestrator**
   - ✅ `app.py` provides Streamlit UI
   - ✅ `query_classifier.py` classifies queries
   - ✅ `orchestrator_v2.py` orchestrates the flow

2. **Data Sources**
   - ✅ **RBI MPR**: `files-mock/analytics/rbi_mpr_data.json` + RAG system
   - ✅ **NSE Bond Data**: `files-mock/analytics/nse_bond_data.json`
   - ✅ **News APIs**: `tools/tools_manager.py` → `create_news_scraper()`
   - ✅ **Portfolio**: `agents/portfolio_manager.py`
   - ✅ **Credit Risk Rating**: `tools/tools_manager.py` → `create_crisil_scraper()`

3. **Agent Flow**
   - ✅ **Orchestrator → Explainability → Analyst → Advisory → UI**
   - ✅ Portfolio → Explainability Agent

4. **Models Exist**
   - ✅ **HLCRIG/Nelson-Siegel**: `models/pathway_yield.py`
   - ✅ **Bond Price Forecasting**: `models/bond_price_forecasting.py`
   - ✅ **Online ML Model**: Referenced in `ml_model_output.json`

### ⚠️ **Missing/Incomplete Integration**

1. **HLCRIG → Online ML Model → Yield Estimates**
   - ⚠️ **Status**: Models exist but not integrated as tools
   - **Location**: `models/pathway_yield.py` (Pathway streaming)
   - **Issue**: No `YIELD_FORECASTER` tool implementation
   - **Needed**: Tool wrapper to call Pathway yield forecasting

2. **Bond Price Calculation**
   - ⚠️ **Status**: Model exists but not integrated as tool
   - **Location**: `models/bond_price_forecasting.py`
   - **Issue**: No `BOND_PRICER` tool implementation
   - **Needed**: Tool wrapper to calculate bond prices from yield estimates

3. **Yield Forecaster Tool**
   - ⚠️ **Status**: Referenced in schemas but not implemented
   - **Schema**: `ToolType.YIELD_FORECASTER` exists in `schemas_v2.py`
   - **Config**: Listed in `config/planner_config.json`
   - **Issue**: Not in `tools_manager.py`
   - **Needed**: Implementation in `tools/tools_manager.py`

4. **Bond Pricer Tool**
   - ⚠️ **Status**: Referenced in schemas but not implemented
   - **Schema**: `ToolType.BOND_PRICER` exists in `schemas_v2.py`
   - **Config**: Listed in `config/planner_config.json`
   - **Issue**: Not in `tools_manager.py`
   - **Needed**: Implementation in `tools/tools_manager.py`

5. **Web Server**
   - ✅ **Status**: Implemented via Streamlit (`app.py`)
   - **Note**: Streamlit serves as the web server/UI

## Current Flow vs Diagram Flow

### **Diagram Flow:**
```
UI → Query Classifier → Orchestrator
RBI MPR → HLCRIG → Online ML Model → Yield Estimates
NSE Bond Data + Yield Estimates → Bond Price
Orchestrator → Explainability (SHAP) → Analyst → Advisory → UI
Portfolio → Explainability Agent
```

### **Current Flow:**
```
UI (Streamlit) → Query Classifier → Orchestrator
RBI MPR (RAG/Mock) → ML Model Agent (Mock Data)
NSE Bond Data (Mock) → Analyst Agent
Orchestrator → Explainability → Analyst → Advisory → UI
Portfolio → Explainability Agent
```

## Key Differences

1. **Yield Forecasting**: 
   - **Diagram**: HLCRIG → Online ML Model → Yield Estimates (streaming)
   - **Current**: Mock data or placeholder (Pathway models exist but not integrated)

2. **Bond Pricing**:
   - **Diagram**: Explicit Bond Price calculation from Yield Estimates + NSE Data
   - **Current**: Integrated in Analyst Agent (uses yield curve but not explicit tool)

3. **Tool Integration**:
   - **Diagram**: Tools are explicit (Yield Forecaster, Bond Pricer)
   - **Current**: Some tools missing (Yield Forecaster, Bond Pricer not implemented)

## Recommendations

### **Priority 1: Integrate Yield Forecaster Tool**
- Create `create_yield_forecaster()` in `tools/tools_manager.py`
- Wrap `models/pathway_yield.py` functionality
- Return `YieldCurveForecast` from `schemas_v2.py`
- Integrate with orchestrator's tool execution

### **Priority 2: Integrate Bond Pricer Tool**
- Create `create_bond_pricer()` in `tools/tools_manager.py`
- Wrap `models/bond_price_forecasting.py` functionality
- Use yield forecasts from Yield Forecaster
- Return `BondPriceForecast` from `schemas_v2.py`

### **Priority 3: Update Orchestrator**
- Add Yield Forecaster and Bond Pricer to tools dict
- Update `_execute_tools_parallel()` to handle these tools
- Pass yield forecasts to ML Model Agent
- Pass bond prices to Analyst Agent

### **Priority 4: Update ML Model Agent**
- Accept yield forecasts from Yield Forecaster tool
- Use forecasts in prediction logic
- Integrate with Pathway models when available

## Implementation Status

| Component | Diagram | Current | Status |
|-----------|---------|---------|--------|
| UI | ✅ | ✅ Streamlit | ✅ Match |
| Query Classifier | ✅ | ✅ | ✅ Match |
| Orchestrator | ✅ | ✅ | ✅ Match |
| RBI MPR | ✅ | ✅ Mock/RAG | ✅ Match |
| NSE Bond Data | ✅ | ✅ Mock | ✅ Match |
| News APIs | ✅ | ✅ Tool | ✅ Match |
| Portfolio | ✅ | ✅ Manager | ✅ Match |
| Credit Risk | ✅ | ✅ Tool | ✅ Match |
| HLCRIG | ✅ | ✅ Model exists | ⚠️ Not integrated |
| Online ML Model | ✅ | ✅ Model exists | ⚠️ Not integrated |
| Yield Forecaster | ✅ | ❌ | ❌ Missing |
| Bond Pricer | ✅ | ❌ | ❌ Missing |
| Bond Price | ✅ | ✅ In Analyst | ⚠️ Not explicit |
| Explainability | ✅ | ✅ | ✅ Match |
| Analyst | ✅ | ✅ | ✅ Match |
| Advisory | ✅ | ✅ | ✅ Match |

## Next Steps

1. **Implement Yield Forecaster Tool** (High Priority)
2. **Implement Bond Pricer Tool** (High Priority)
3. **Update Orchestrator** to use new tools
4. **Update ML Model Agent** to use yield forecasts
5. **Test end-to-end** with real Pathway models

