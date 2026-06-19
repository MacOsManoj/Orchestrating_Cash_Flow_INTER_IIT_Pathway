import { NEWS_API_BASE_URL } from "./news";

export interface StockDataPoint {
  ticker: string;
  date: string;
  close_price: number;
  open_price: number;
  volume: number;
  high_price: number;
  low_price: number;
  abs_change: number;
  pct_change: number;
  action: string;
  stop_loss: number;
  take_profit: number;
  signal_strength: number;
  limit_order: number;
  current_price: number;
  rsi: number;
  macd: number;
  macd_signal: number;
  macd_hist: number;
  vwap: number;
  bol_bands: number[];
  sma: number[];
  crsi: number;
  klinger: number[];
  keltner: number[];
  cmo: number;
  reason: string;
  time: number;
  diff: number;
}

export async function fetchStockData(ticker: string, limit: number = 100): Promise<StockDataPoint[]> {
  const response = await fetch(`${NEWS_API_BASE_URL}/api/stocks/${ticker}?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch stock data for ${ticker}`);
  }
  return response.json();
}

export async function fetchAvailableTickers(): Promise<string[]> {
  const response = await fetch(`${NEWS_API_BASE_URL}/api/stocks/`);
  if (!response.ok) {
    throw new Error("Failed to fetch available tickers");
  }
  return response.json();
}
