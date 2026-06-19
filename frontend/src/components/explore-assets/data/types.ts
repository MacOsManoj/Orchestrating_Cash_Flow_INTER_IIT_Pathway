export interface MarketIndex {
  id: string
  name: string
  value: number
  change: number
  changePercent: number
  trend: "up" | "down"
  chartData: number[]
}

export interface Asset {
  id: string
  name: string
  ticker: string
  assetType: "bonds" | "stocks" | "forex"
  // Bond specific
  priceOfPar?: number
  yieldToMaturity?: string
  coupon?: string
  maturityDate?: string
  duration?: number
  changeBps?: number
  // Stock specific
  price?: number
  change?: number
  changePercent?: number
  volume?: string
  rsi?: number
  vwap?: number
  signalStrength?: number
  action?: string
  // Forex specific
  currentPrice?: number
  previousClose?: number
  high?: number
  low?: number
  // Common
  region: string
  sector: string
}

export interface FilterOption {
  label: string
  value: string
}
