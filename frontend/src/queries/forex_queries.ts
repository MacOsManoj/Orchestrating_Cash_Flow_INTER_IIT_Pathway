import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = `${import.meta.env.VITE_API_BASE_URL}/forex`;

// ============================================================================
// TYPES
// ============================================================================

export interface ForexPairSummary {
  pair: string;
  current_price: number;
  previous_close: number;
  price_change_1d: number;
  price_change_pct_1d: number;
  high_1d?: number;
  low_1d?: number;
}

export interface RecommendedTrade {
  pair: string;
  current_price: number;
  price_change_pct: number;
  action: 'buy' | 'sell' | 'hold';
  signal_strength: 'weak' | 'moderate' | 'strong';
  model_confidence: number;
  predicted_return: number;
  stop_loss?: number;
  take_profit?: number;
}

export interface PriceDataPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface CurrencyPriceData {
  pair: string;
  data: PriceDataPoint[];
  spot_rate: number;
  realized_volatility_10d: number;
  realized_volatility_20d: number;
  atr_14d: number;
  timestamp: string;
}

export interface RiskMetrics {
  pair: string;
  volatility_10d: number;
  volatility_20d: number;
  volatility_60d: number;
  value_at_risk_95: number;
  value_at_risk_99: number;
  position_size: number;
  strategy_sharpe: number;
  max_drawdown_pct: number;
  beta_to_usd?: number;
  timestamp: string;
}

export interface PortfolioExposure {
  pair: string;
  avg_buy_price?: number;
  avg_sell_price?: number;
  current_position: 'long' | 'short' | 'flat';
  position_size: number;
  realized_pnl: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  portfolio_exposure_pct: number;
  entry_date?: string;
  days_held: number;
  timestamp: string;
}

export interface PortfolioSummary {
  total_open_positions: number;
  total_exposure_long: number;
  total_exposure_short: number;
  net_exposure: number;
  total_unrealized_pnl_pct: number;
  portfolio_heat: number;
  long_exposure_pct: number;
  short_exposure_pct: number;
  positions: Record<string, any>;
  timestamp: string;
}

export interface TradeActionRequest {
  pair: string;
  action: 'buy' | 'sell' | 'hold';
  amount?: number;
  price?: number;
}

export interface CumulativeProfit {
  pair: string;
  total_profit_pct: number;
  total_profit_amount: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_profit_per_trade: number;
  largest_win_pct: number;
  largest_loss_pct: number;
  current_streak: number;
  profit_history: any[];
  timestamp: string;
}

export interface CorrelationMatrix {
  pairs: string[];
  matrix: number[][];
  period_days: number;
  timestamp: string;
}

export interface HeadlineSentiment {
  pairs: {
    pair: string;
    overall_sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
    sentiment_score: number;
    confidence: 'high' | 'medium' | 'low';
    headline_count: number;
    headlines: {
      title: string;
      source: string;
      sentiment: string;
      sentiment_score: number;
      url?: string;
      published_date?: string;
    }[];
  }[];
  market_sentiment: string;
  market_sentiment_score: number;
  timestamp: string;
}

// ============================================================================
// MAIN PAGE QUERIES
// ============================================================================

// Get all forex pairs overview
export const useForexPairs = () => {
  return useQuery({
    queryKey: ['forex', 'pairs'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/pairs`);
      if (!res.ok) throw new Error('Failed to fetch forex pairs');
      return res.json() as Promise<{ pairs: ForexPairSummary[]; timestamp: string }>;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

// Get recommended trades
export const useRecommendedTrades = () => {
  return useQuery({
    queryKey: ['forex', 'recommended-trades'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/recommended-trades`);
      if (!res.ok) throw new Error('Failed to fetch recommended trades');
      return res.json() as Promise<{ trades: RecommendedTrade[]; timestamp: string }>;
    },
    refetchInterval: 60000,
  });
};

// Get portfolio summary
export const usePortfolioSummary = () => {
  return useQuery({
    queryKey: ['forex', 'portfolio'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/portfolio`);
      if (!res.ok) throw new Error('Failed to fetch portfolio');
      return res.json() as Promise<PortfolioSummary>;
    },
    refetchInterval: 30000,
  });
};

// Execute trade action (buy/sell/hold)
export const useExecuteTrade = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (request: TradeActionRequest) => {
      const res = await fetch(`${API_BASE}/v1/trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!res.ok) throw new Error('Failed to execute trade');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forex', 'portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['forex', 'recommended-trades'] });
      queryClient.invalidateQueries({ queryKey: ['forex', 'positions'] });
    },
  });
};

// ============================================================================
// CURRENCY PAGE QUERIES
// ============================================================================

// Get price data for a currency pair
export const useCurrencyPriceData = (pair: string, days: number = 90) => {
  return useQuery({
    queryKey: ['forex', 'price-data', pair, days],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/currency/${pair}/price-data?days=${days}`);
      if (!res.ok) throw new Error(`Failed to fetch price data for ${pair}`);
      return res.json() as Promise<CurrencyPriceData>;
    },
    enabled: !!pair,
    refetchInterval: 60000,
  });
};

// Get risk metrics for a currency pair
export const useRiskMetrics = (pair: string) => {
  return useQuery({
    queryKey: ['forex', 'risk-metrics', pair],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/currency/${pair}/risk-metrics`);
      if (!res.ok) throw new Error(`Failed to fetch risk metrics for ${pair}`);
      return res.json() as Promise<RiskMetrics>;
    },
    enabled: !!pair,
  });
};

// Get portfolio exposure for a currency pair
export const usePortfolioExposure = (pair: string) => {
  return useQuery({
    queryKey: ['forex', 'exposure', pair],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/currency/${pair}/exposure`);
      if (!res.ok) throw new Error(`Failed to fetch exposure for ${pair}`);
      return res.json() as Promise<PortfolioExposure>;
    },
    enabled: !!pair,
  });
};

// ============================================================================
// PROFIT QUERIES
// ============================================================================

// Get cumulative profit for a pair
export const useCumulativeProfit = (pair: string) => {
  return useQuery({
    queryKey: ['forex', 'profits', pair],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/profits/${pair}`);
      if (!res.ok) throw new Error(`Failed to fetch profits for ${pair}`);
      return res.json() as Promise<CumulativeProfit>;
    },
    enabled: !!pair,
  });
};

// Get all pairs profits
export const useAllPairsProfits = () => {
  return useQuery({
    queryKey: ['forex', 'profits', 'all'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/profits`);
      if (!res.ok) throw new Error('Failed to fetch all profits');
      return res.json();
    },
  });
};

// Get profit chart data
export const useProfitChartData = (pair: string) => {
  return useQuery({
    queryKey: ['forex', 'profits', pair, 'chart'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/profits/${pair}/chart-data`);
      if (!res.ok) throw new Error(`Failed to fetch profit chart for ${pair}`);
      return res.json();
    },
    enabled: !!pair,
  });
};

// ============================================================================
// ANALYSIS QUERIES
// ============================================================================

// Get correlation matrix
export const useCorrelationMatrix = (days: number = 60) => {
  return useQuery({
    queryKey: ['forex', 'correlation', days],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/correlation-matrix?days=${days}`);
      if (!res.ok) throw new Error('Failed to fetch correlation matrix');
      return res.json() as Promise<CorrelationMatrix>;
    },
  });
};

// Get trade records
export const useTradeRecords = (pair?: string, limit: number = 50) => {
  return useQuery({
    queryKey: ['forex', 'trade-records', pair, limit],
    queryFn: async () => {
      const url = pair 
        ? `${API_BASE}/v1/trade-records?pair=${pair}&limit=${limit}`
        : `${API_BASE}/v1/trade-records?limit=${limit}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch trade records');
      return res.json();
    },
  });
};

// Get headline sentiment
export const useHeadlineSentiment = () => {
  return useQuery({
    queryKey: ['forex', 'headline-sentiment'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/headlines/sentiment`);
      if (!res.ok) throw new Error('Failed to fetch headline sentiment');
      return res.json() as Promise<HeadlineSentiment>;
    },
    refetchInterval: 300000, // Refetch every 5 minutes
  });
};

// ============================================================================
// POSITIONS & TRADES (Legacy)
// ============================================================================

export const useAllPositions = () => {
  return useQuery({
    queryKey: ['forex', 'positions', 'all'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/positions`);
      if (!res.ok) throw new Error('Failed to fetch positions');
      return res.json();
    },
    refetchInterval: 30000,
  });
};

export const usePosition = (pair: string) => {
  return useQuery({
    queryKey: ['forex', 'positions', pair],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/positions/${pair}`);
      if (!res.ok) throw new Error(`Failed to fetch position for ${pair}`);
      return res.json();
    },
    enabled: !!pair,
  });
};

// ============================================================================
// AGENT QUERIES
// ============================================================================

export const useAgentQuery = () => {
  return useMutation({
    mutationFn: async (query: string) => {
      const res = await fetch(`${API_BASE}/v1/agent/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) throw new Error('Agent query failed');
      return res.json();
    },
  });
};