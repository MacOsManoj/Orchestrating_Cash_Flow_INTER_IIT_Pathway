// src/components/playground-components/index.ts
import React from "react"
import type { CanvasComponentDefinition, ComponentSize } from "../CanvasLayout"
import { CorrelationMatrixFX } from "./CorrelationMatrixFX"
import { NewsSentimentStream } from "./NewsSentimentStream"
import { AssetPerformance } from "./AssetPerformance"
import { CashAllocationCard } from "./CashAllocationCard"
import { LiquidityDashboard } from "./LiquidityDashboard"
import { FundamentalsCard } from "./FundamentalsCard"
import { SentimentAnalysisCard } from "./SentimentAnalysisCard"
import { StockPriceHeader } from "./StockPriceHeader"
import { BondTermsCard } from "./BondTermsCard"
import { CashFlowTable } from "./CashFlowTable"
import { AllocationDashboard } from "./AllocationDashboard"
import { AlertsInsights } from "./AlertsInsights"
import { BondRiskSensitivity } from "./BondRiskSensitivity"
import { BondPricingCard } from "./BondPricingCard"
import { CashBalanceForecastChart } from "./CashBalanceForecastChart"
import { FxPriceChart } from "./FxPriceChart"
import { StockCandlestickChart } from "./StockCandlestickChart"
import { BondYieldTimeChart } from "./BondYieldTimeChart"
import { RateVsYieldChart } from "./RateVsYieldChart"
import { BondPriceTimeChart } from "./BondPriceTimeChart"
import { MonteCarloOutputCard } from "./MonteCarloOutputCard"

// Helper function to get safe default size
function getSize(staticSize?: ComponentSize): ComponentSize {
  return staticSize && ["full", "large", "medium", "small"].includes(staticSize)
    ? staticSize
    : "medium"
}

export const ComponentRegistry: Record<string, CanvasComponentDefinition> = {
  AssetPerformance: {
    component: AssetPerformance,
    defaultSize: getSize((AssetPerformance as any).canvasSize) as ComponentSize,
  },
  CashAllocationCard: {
    component: CashAllocationCard,
    defaultSize: getSize((CashAllocationCard as any).canvasSize) as ComponentSize,
  },
  LiquidityDashboard: {
    component: LiquidityDashboard,
    defaultSize: getSize((LiquidityDashboard as any).canvasSize) as ComponentSize,
  },
  FundamentalsCard: {
    component: FundamentalsCard,
    defaultSize: getSize((FundamentalsCard as any).canvasSize) as ComponentSize,
  },
  SentimentAnalysisCard: {
    component: SentimentAnalysisCard,
    defaultSize: getSize((SentimentAnalysisCard as any).canvasSize) as ComponentSize,
  },
  StockPriceHeader: {
    component: StockPriceHeader,
    defaultSize: getSize((StockPriceHeader as any).canvasSize) as ComponentSize,
  },
  BondTermsCard: {
    component: BondTermsCard,
    defaultSize: getSize((BondTermsCard as any).canvasSize) as ComponentSize,
  },
  CashFlowTable: {
    component: CashFlowTable,
    defaultSize: "full" as ComponentSize,
  },
  NewsSentimentStream: {
    component: NewsSentimentStream,
    defaultSize: getSize((NewsSentimentStream as any).canvasSize) as ComponentSize,
  },
  CorrelationMatrixFX: {
    component: CorrelationMatrixFX,
    defaultSize: "large" as ComponentSize,
  },
  AllocationDashboard: {
    component: AllocationDashboard,
    defaultSize: getSize((AllocationDashboard as any).canvasSize) as ComponentSize,
  },
  AlertsInsights: {
    component: AlertsInsights,
    defaultSize: "large" as ComponentSize,
  },
  BondRiskSensitivity: {
    component: BondRiskSensitivity,
    defaultSize: "small" as ComponentSize,
  },
  BondPricingCard: {
    component: BondPricingCard,
    defaultSize: "small" as ComponentSize,
  },
  CashBalanceForecastChart: {
    component: CashBalanceForecastChart,
    defaultSize: "large" as ComponentSize,
  },
  FxPriceChart: {
    component: FxPriceChart,
    defaultSize: "large" as ComponentSize,
  },
  StockCandlestickChart: {
    component: StockCandlestickChart,
    defaultSize: "large" as ComponentSize,
  },
  BondYieldTimeChart: {
    component: BondYieldTimeChart,
    defaultSize: "large" as ComponentSize,
  },
  RateVsYieldChart: {
    component: RateVsYieldChart,
    defaultSize: getSize((RateVsYieldChart as any).canvasSize) as ComponentSize,
  },
  BondPriceTimeChart: {
    component: BondPriceTimeChart,
    defaultSize: "large" as ComponentSize,
  },
  MonteCarloOutputCard: {
    component: MonteCarloOutputCard,
    defaultSize: getSize((MonteCarloOutputCard as any).canvasSize) as ComponentSize,
  },
}

// Simple alias if some parts of the app just want "type → component"
export const ComponentMap: Record<string, React.ComponentType<any>> = Object.fromEntries(
  Object.entries(ComponentRegistry).map(([type, def]) => [type, def.component]),
)
