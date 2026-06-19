import { useQuery } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

// ============================================================================
// TYPES - Based on backend Pydantic models
// ============================================================================

export interface BondDetails {
  isin: string;
  bond_name: string;
  symbol?: string;
  coupon_rate?: number;
  maturity_date: string;
  next_coupon_date?: string;
  minimum_increment: number;
  last_price: number;
  clean_price: number;
  accrued_interest: number;
  duration: number;
  convexity: number;
  dv01: number;
  z_spread: number;
  var: number;
  ytm?: number;
  interest_rate_volatility?: number;
  credit_spread_volatility?: number;
  credit_rating?: string;
}

export interface BondSummary {
  isin: string;
  bond_name: string;
  coupon_rate?: number;
  maturity_date: string;
  last_price: number;
}

export interface YieldDataPoint {
  date: string;
  yield: number;
  time: string;
}

export interface YieldMetrics {
  current_yielding: number;
  current_yielding_percent: number;
  one_month_change: number;
  one_month_change_unit: string;
  volatility_20d: number;
  volatility_20d_percent: number;
  max_drawdown_1y: number;
  max_drawdown_1y_percent: number;
}

export interface YieldHistoryResponse {
  isin: string;
  period: string;
  yield_data: YieldDataPoint[];
  metrics: YieldMetrics;
  last_updated: string;
}

export interface RateYieldDataPoint {
  date: string;
  policy_rate: number;
  yield_10y: number;
}

export interface SeriesDefinition {
  name: string;
  data_key: string;
  color: string;
  y_axis: string;
}

export interface YAxisConfig {
  label: string;
  min: number;
  max: number;
}

export interface RateYieldOverlayResponse {
  isin: string;
  period: string;
  data: RateYieldDataPoint[];
  series: SeriesDefinition[];
  y_axes: Record<string, YAxisConfig>;
  last_updated: string;
}

export interface PriceStatisticsDataPoint {
  date: string;
  price: number;
  price_5th_percentile: number;
  price_95th_percentile: number;
}

export interface PriceStatisticsMetrics {
  median_price: number;
  price_5th_percentile: number;
  price_95th_percentile: number;
  implied_volatility: number;
}

export interface PriceStatisticsResponse {
  isin: string;
  period: string;
  price_data: PriceStatisticsDataPoint[];
  metrics: PriceStatisticsMetrics;
  last_updated: string;
}

export interface FinancialMetrics {
  revenue_impact: string;
  stock_price_impact: string;
  confidence: string;
}

export interface SummarizedArticle {
  article_id: string;
  title: string;
  url: string;
  company: string;
  factor_type: string;
  published_at: string;
  source: string;
  content: string;
  sentiment_label: string;
  sentiment_score: number;
  liquidity_impact: string;
  is_relevant: boolean;
  relevance_reason: string;
  summary: string;
  financial_metrics: FinancialMetrics;
  impact_assessment: string;
}

export interface BondSearchResult {
  isin: string;
  name: string;
  issuer: string;
  coupon_rate: number;
  maturity_date: string;
  current_yield: number;
  current_yield_percent: number;
  yield_change: number;
  yield_change_direction: "up" | "down" | "neutral";
}

export interface SearchResponse {
  results: BondSearchResult[];
  total_results: number;
}

// ============================================================================
// QUERY OPTIONS WITH RETRY & EXPONENTIAL BACKOFF
// ============================================================================

const defaultQueryOptions = {
  retry: 3,
  retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
  staleTime: 30000, // 30 seconds
  refetchOnWindowFocus: false,
};

// ============================================================================
// BOND QUERIES
// ============================================================================

/**
 * Fetch bond details by ISIN
 * Returns comprehensive bond information including pricing, risk metrics, and characteristics
 */
export const useBondDetails = (isin: string | undefined) => {
  return useQuery({
    queryKey: ["bond", "details", isin],
    queryFn: async (): Promise<BondDetails> => {
      const res = await fetch(`${API_BASE}/bonds/${isin}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch bond details: ${res.status}`);
      }
      return res.json();
    },
    enabled: !!isin,
    ...defaultQueryOptions,
  });
};

/**
 * Fetch bond universe - all available bonds
 */
export const useBondUniverse = () => {
  return useQuery({
    queryKey: ["bond", "universe"],
    queryFn: async (): Promise<BondSummary[]> => {
      const res = await fetch(`${API_BASE}/bonds/universe`);
      if (!res.ok) {
        throw new Error(`Failed to fetch bond universe: ${res.status}`);
      }
      return res.json();
    },
    ...defaultQueryOptions,
  });
};

/**
 * Fetch yield history for a bond
 * @param isin - Bond ISIN
 * @param period - Time period: 1D, 1W, 1M, 1Y, YTD, MAX
 */
export const useYieldHistory = (
  isin: string | undefined,
  period: "1D" | "1W" | "1M" | "1Y" | "YTD" | "MAX" = "1D"
) => {
  return useQuery({
    queryKey: ["bond", "yield-history", isin, period],
    queryFn: async (): Promise<YieldHistoryResponse> => {
      const res = await fetch(`${API_BASE}/bonds/${isin}/yield-history?period=${period}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch yield history: ${res.status}`);
      }
      return res.json();
    },
    enabled: !!isin,
    ...defaultQueryOptions,
  });
};

/**
 * Fetch rate vs yield overlay data
 * @param isin - Bond ISIN
 * @param period - Time period: 5Y, 3Y, 1Y, YTD
 */
export const useRateYieldOverlay = (
  isin: string | undefined,
  period: "5Y" | "3Y" | "1Y" | "YTD" = "1Y"
) => {
  return useQuery({
    queryKey: ["bond", "rate-yield-overlay", isin, period],
    queryFn: async (): Promise<RateYieldOverlayResponse> => {
      const res = await fetch(`${API_BASE}/bonds/${isin}/rate-yield-overlay?period=${period}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch rate/yield overlay: ${res.status}`);
      }
      return res.json();
    },
    enabled: !!isin,
    ...defaultQueryOptions,
  });
};

/**
 * Fetch price statistics for a bond
 * @param isin - Bond ISIN
 * @param period - Time period: 1D, 1W, 1M, 3M, YTD, 1Y, MAX
 */
export const usePriceStatistics = (
  isin: string | undefined,
  period: "1D" | "1W" | "1M" | "3M" | "YTD" | "1Y" | "MAX" = "1D"
) => {
  return useQuery({
    queryKey: ["bond", "price-statistics", isin, period],
    queryFn: async (): Promise<PriceStatisticsResponse> => {
      const res = await fetch(`${API_BASE}/bonds/${isin}/price-statistics?period=${period}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch price statistics: ${res.status}`);
      }
      return res.json();
    },
    enabled: !!isin,
    ...defaultQueryOptions,
  });
};

/**
 * Fetch summarized news articles
 * @param company - Company name
 * @param limit - Max results
 */
export const useSummarizedNews = (company: string, limit: number = 5) => {
  return useQuery({
    queryKey: ["news", "summarized", company],
    queryFn: async (): Promise<SummarizedArticle[]> => {
      const params = new URLSearchParams({
        company: company,
        limit: limit.toString(),
      });
      const res = await fetch(`${API_BASE}/news/summarized?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch news: ${res.status}`);
      }
      return res.json();
    },
    enabled: !!company,
    ...defaultQueryOptions,
  });
};

/**
 * Search bonds for comparison
 * @param query - Search query (ISIN or name)
 * @param limit - Max results
 */
export const useBondSearch = (query: string, limit: number = 10) => {
  return useQuery({
    queryKey: ["bond", "search", query, limit],
    queryFn: async (): Promise<SearchResponse> => {
      const params = new URLSearchParams({
        query: query,
        limit: limit.toString(),
      });
      const res = await fetch(`${API_BASE}/bonds/compare/search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Failed to search bonds: ${res.status}`);
      }
      return res.json();
    },
    enabled: query.length >= 2,
    ...defaultQueryOptions,
  });
};

/**
 * Fetch multiple bond details for comparison
 * @param isins - Array of ISINs to fetch
 */
export const useMultipleBondDetails = (isins: string[]) => {
  return useQuery({
    queryKey: ["bond", "multiple-details", isins],
    queryFn: async (): Promise<BondDetails[]> => {
      const results = await Promise.all(
        isins.map(async (isin) => {
          const res = await fetch(`${API_BASE}/bonds/${isin}`);
          if (!res.ok) {
            throw new Error(`Failed to fetch bond details for ${isin}: ${res.status}`);
          }
          return res.json();
        })
      );
      return results;
    },
    enabled: isins.length > 0,
    ...defaultQueryOptions,
  });
};

/**
 * Fetch multiple price statistics for comparison
 * @param isins - Array of ISINs
 * @param period - Time period
 */
export const useMultiplePriceStatistics = (
  isins: string[],
  period: "1D" | "1W" | "1M" | "3M" | "YTD" | "1Y" | "MAX" = "1M"
) => {
  return useQuery({
    queryKey: ["bond", "multiple-price-statistics", isins, period],
    queryFn: async (): Promise<PriceStatisticsResponse[]> => {
      const results = await Promise.all(
        isins.map(async (isin) => {
          const res = await fetch(`${API_BASE}/bonds/${isin}/price-statistics?period=${period}`);
          if (!res.ok) {
            throw new Error(`Failed to fetch price statistics for ${isin}: ${res.status}`);
          }
          return res.json();
        })
      );
      return results;
    },
    enabled: isins.length > 0,
    ...defaultQueryOptions,
  });
};
