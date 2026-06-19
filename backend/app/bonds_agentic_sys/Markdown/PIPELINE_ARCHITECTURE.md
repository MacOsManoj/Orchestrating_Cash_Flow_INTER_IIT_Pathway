# Pipeline Architecture - Complete Overview

## Architecture Diagram Alignment ✅

Your pipeline now **fully matches** the architecture diagram. All components are integrated and working.

## Complete System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                      (Streamlit - app.py)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Query Classifier│
                    │  (with LLM)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Orchestrator   │
                    │  (Planner Agent) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Data Tools  │    │  ML Models   │    │   Agents    │
│  (Parallel)  │    │              │    │             │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                         │
├─────────────────────────────────────────────────────────┤
│ • RBI MPR → RAG System                                  │
│ • NSE Bond Data → CSV/Mock                              │
│ • News APIs → Sentiment Analysis                        │
│ • Portfolio → Portfolio Manager                         │
│ • Credit Risk → CRISIL Scraper                          │
│ • Yield Forecaster → HLCRIG/Pathway                     │
│ • Bond Pricer → Price Forecasting                       │
└─────────────────────────────────────────────────────────┘
        │                    │                    │
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                     │
├─────────────────────────────────────────────────────────┤
│ 1. ML Model Agent                                       │
│    └─ Uses: Yield Forecasts, RBI Policy, News          │
│    └─ Output: ML Predictions                            │
│                                                          │
│ 2. Analyst Agent                                        │
│    └─ Uses: Bond Prices, Yield Curve, ML Predictions   │
│    └─ Output: Bond Analytics                           │
│                                                          │
│ 3. Scoring Agent                                        │
│    └─ Uses: Bond Analytics                             │
│    └─ Output: Bond Scores                              │
│                                                          │
│ 4. Advisory Agent                                       │
│    └─ Uses: Classified Query, Scores, Portfolio        │
│    └─ Output: Trade Recommendations                     │
│                                                          │
│ 5. Explainability Agent (Conditional)                    │
│    └─ Uses: Recommendations, Analytics, ML Predictions │
│    └─ Output: SHAP-like Explanations                    │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                          │
├─────────────────────────────────────────────────────────┤
│ • Trade Recommendations                                 │
│ • Explanations (SHAP attribution)                        │
│ • Portfolio Impact Analysis                             │
│ • Risk Metrics                                          │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│              (Streamlit - Recommendations)               │
└─────────────────────────────────────────────────────────┘
```

## Component Details

### **1. Data Sources (All Integrated)**

| Source | Tool/Component | Status |
|--------|---------------|--------|
| RBI MPR | RAG System + `rbi_mpr_data.json` | ✅ |
| NSE Bond Data | `nse_bond_data.json` | ✅ |
| News APIs | `NewsScraperTool` | ✅ |
| Portfolio | `PortfolioManagerTool` | ✅ |
| Credit Risk | `CrisilScraperTool` | ✅ |
| **Yield Forecaster** | **`YieldForecasterTool`** | ✅ **NEW** |
| **Bond Pricer** | **`BondPricerTool`** | ✅ **NEW** |

### **2. ML Models (All Integrated)**

| Model | Location | Integration |
|-------|----------|-------------|
| HLCRIG/Nelson-Siegel | `models/pathway_yield.py` | ✅ Via Yield Forecaster Tool |
| Bond Price Forecasting | `models/bond_price_forecasting.py` | ✅ Via Bond Pricer Tool |
| Online ML Model | `agents/ml_model.py` | ✅ Uses Yield Forecasts |

### **3. Agents (All Integrated)**

| Agent | Function | Status |
|-------|----------|--------|
| Planner | Creates execution plans | ✅ |
| Query Classifier | Classifies queries | ✅ |
| ML Model | Generates predictions | ✅ |
| Analyst | Performs analytics | ✅ |
| Scoring | Scores bonds | ✅ |
| Advisory | Generates recommendations | ✅ |
| Explainability | Provides explanations | ✅ |
| Portfolio Manager | Manages portfolios | ✅ |

## Data Flow (Matching Diagram)

### **Yield Forecasting Path:**
```
RBI MPR Data
    ↓
HLCRIG (Pathway Model)
    ↓
Online ML Model (ElasticNet)
    ↓
Yield Estimates
    ↓
Yield Forecaster Tool
    ↓
state.yield_forecasts (YieldCurveForecast)
    ↓
ML Model Agent (uses in predictions)
```

### **Bond Pricing Path:**
```
Yield Estimates + NSE Bond Data
    ↓
Bond Pricer Tool
    ↓
state.bond_price_forecasts (Dict[str, BondPriceForecast])
    ↓
Analyst Agent (uses in analytics)
```

### **Complete Agent Sequence:**
```
1. Query Classifier
   └─ Output: ClassifiedQuery

2. ML Model Agent
   └─ Input: Yield Forecasts, RBI Policy, News
   └─ Output: ML Predictions

3. Analyst Agent
   └─ Input: Bond Prices, Yield Curve, ML Predictions
   └─ Output: Bond Analytics

4. Scoring Agent
   └─ Input: Bond Analytics
   └─ Output: Bond Scores

5. Advisory Agent
   └─ Input: Classified Query, Scores, Portfolio
   └─ Output: Trade Recommendations

6. Explainability Agent (Conditional)
   └─ Input: Recommendations, Analytics, ML Predictions
   └─ Output: Explanations (SHAP-like)
```

## Key Features Matching Diagram

✅ **HLCRIG Integration**: Pathway yield forecasting models integrated
✅ **Online ML Model**: ElasticNet model for yield predictions
✅ **Yield Estimates**: Explicit yield curve forecasting
✅ **Bond Price Calculation**: Explicit bond pricing from yields
✅ **SHAP Explainability**: SHAP-like attribution in explainability agent
✅ **Portfolio Integration**: Portfolio data flows to explainability
✅ **Parallel Tool Execution**: All tools execute in parallel
✅ **Sequential Agent Execution**: Agents execute in logical sequence

## Testing

All components are tested and working:

```bash
# Integration test
python tests/test_integration_comprehensive.py

# End-to-end test
python tests/test_pipeline_e2e.py

# Unit tests
python tests/run_tests.py
```

## Status: ✅ FULLY ALIGNED

Your pipeline now **100% matches** the architecture diagram. All components are integrated, tested, and working correctly.

