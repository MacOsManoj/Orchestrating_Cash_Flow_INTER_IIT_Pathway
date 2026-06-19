// frontend/src/api/portfolio.ts

import { NEWS_API_BASE_URL } from "./news";

// ============================================================================
// TYPES
// ============================================================================

export interface TradeRequest {
  asset_type: "stocks" | "bonds" | "forex";
  ticker: string;
  action: "buy" | "sell";
  quantity: number;
  price: number;
  asset_name?: string;
}

export interface TradeResponse {
  trade_id: string;
  status: string;
  message: string;
  trade: {
    asset_type: string;
    ticker: string;
    asset_name: string;
    action: string;
    quantity: number;
    price: number;
    total_value: number;
    executed_at: string;
    status: string;
    _id: string;
  };
}

export interface AssetBreakdown {
  amount: number;
  percentage: number;
}

export interface PortfolioDistribution {
  total_portfolio_value: number;
  free_cash: number;
  invested_amount: number;
  loans: number;
  total_deposits: number;
  asset_breakdown: {
    govt_bonds: AssetBreakdown;
    stocks: AssetBreakdown;
    forex: AssetBreakdown;
    free_cash: AssetBreakdown;
  };
  last_updated?: string;
}

export interface TradeRecord {
  _id: string;
  asset_type: string;
  ticker: string;
  asset_name: string;
  action: string;
  quantity: number;
  price: number;
  total_value: number;
  executed_at: string;
  status: string;
}

export interface TradeHistoryResponse {
  trades: TradeRecord[];
  count: number;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Execute a trade (buy or sell)
 */
export async function executeTrade(trade: TradeRequest): Promise<TradeResponse> {
  const response = await fetch(`${NEWS_API_BASE_URL}/api/portfolio/trade`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(trade),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to execute trade");
  }

  return response.json();
}

/**
 * Get initial asset distribution
 */
export async function getInitialDistribution(): Promise<PortfolioDistribution> {
  const response = await fetch(`${NEWS_API_BASE_URL}/api/portfolio/initial-distribution`);

  if (!response.ok) {
    throw new Error("Failed to fetch initial distribution");
  }

  return response.json();
}

/**
 * Get current asset distribution
 */
export async function getCurrentDistribution(): Promise<PortfolioDistribution> {
  const response = await fetch(`${NEWS_API_BASE_URL}/api/portfolio/current-distribution`);

  if (!response.ok) {
    throw new Error("Failed to fetch current distribution");
  }

  return response.json();
}

/**
 * Get trade history
 */
export async function getTradeHistory(
  assetType?: string,
  ticker?: string,
  limit: number = 50
): Promise<TradeHistoryResponse> {
  const params = new URLSearchParams();
  if (assetType) params.append("asset_type", assetType);
  if (ticker) params.append("ticker", ticker);
  params.append("limit", limit.toString());

  const response = await fetch(
    `${NEWS_API_BASE_URL}/api/portfolio/trades?${params.toString()}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch trade history");
  }

  return response.json();
}

/**
 * Reset portfolio state (for testing)
 */
export async function resetPortfolioState(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${NEWS_API_BASE_URL}/api/portfolio/reset-state`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Failed to reset portfolio state");
  }

  return response.json();
}
