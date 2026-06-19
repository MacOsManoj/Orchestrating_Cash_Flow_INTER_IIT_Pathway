// Stock data types
export interface StockData {
  name: string
  price: number
  currency: string
  priceChange: number
  priceChangePercent: number
  timestamp: string
  exchange: string
  currentValue: number
  investedAmount: number
  highValue: number
  lowValue: number
}

export interface MetricItem {
  label: string
  value?: string | number
}

export interface SummaryData {
  title: string
  points: string[]
}

export interface NewsItem {
  id: string
  title?: string
  description?: string
  timestamp?: string
}

export interface ChartDataPoint {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// Technical and Fundamental data types
export interface TechnicalData {
  rsi: string
  macd: string
  movingAverage50: string
  movingAverage200: string
  support: string
  resistance: string
}

export interface FundamentalData {
  peRatio: string
  pbRatio: string
  debtToEquity: string
  currentRatio: string
  epsGrowth: string
  revenueGrowth: string
}

// Sample stock data
export const stockData: StockData = {
  name: "Stock Name",
  price: 98,
  currency: "INR",
  priceChange: -1.47,
  priceChangePercent: -1.5,
  timestamp: "Nov 4, 3:59:53 PM UTC+5:30",
  exchange: "NSE",
  currentValue: 9795900,
  investedAmount: 9800000,
  highValue: 1034,
  lowValue: 404,
}

// Metrics data
export const metricsData: MetricItem[] = [
  { label: "Return on Equity (ROE):", value: "" },
  { label: "Stock P/E:", value: "" },
  { label: "Market Cap:", value: "" },
  { label: "Beta:", value: "" },
  { label: "Return on Capital (ROCE):", value: "" },
  { label: "Dividend Yield:", value: "" },
  { label: "Free Cash Flow (FCF):", value: "" },
  { label: "Revenue Growth-YoY:", value: "" },
  { label: "EPS growth-YoY:", value: "" },
]

// Summary data
export const summaryData: SummaryData = {
  title: "Summary:",
  points: ["2 to 3 points about the company"],
}

// PROS and CONS data
export const prosData: string[] = []
export const consData: string[] = []

// Chart time periods
export const timePeriods = [
  { label: "1D", value: "1d" },
  { label: "1W", value: "1w" },
  { label: "1M", value: "1m" },
  { label: "1Y", value: "1y" },
]

// Chart indicators
export const chartIndicators = [
  { label: "Volume", value: "volume" },
  { label: "50 DMA", value: "50dma" },
  { label: "Fx +", value: "fx" },
]

// Sample chart data (candlestick)
export const chartData: ChartDataPoint[] = [
  { time: 1, open: 170, high: 175, low: 168, close: 172, volume: 45 },
  { time: 2, open: 172, high: 178, low: 171, close: 176, volume: 50 },
  { time: 3, open: 176, high: 180, low: 174, close: 175, volume: 55 },
  { time: 4, open: 175, high: 177, low: 170, close: 171, volume: 48 },
  { time: 5, open: 171, high: 174, low: 168, close: 170, volume: 52 },
  { time: 6, open: 170, high: 176, low: 169, close: 174, volume: 60 },
  { time: 7, open: 174, high: 179, low: 173, close: 177, volume: 58 },
  { time: 8, open: 177, high: 180, low: 175, close: 178, volume: 62 },
  { time: 9, open: 178, high: 181, low: 176, close: 179, volume: 65 },
  { time: 10, open: 179, high: 182, low: 177, close: 180, volume: 70 },
  { time: 11, open: 180, high: 178, low: 172, close: 174, volume: 68 },
  { time: 12, open: 174, high: 176, low: 170, close: 171, volume: 72 },
  { time: 13, open: 171, high: 173, low: 167, close: 169, volume: 75 },
  { time: 14, open: 169, high: 172, low: 165, close: 167, volume: 80 },
]

// Recent news data
export const recentNews: NewsItem[] = [{ id: "1" }, { id: "2" }, { id: "3" }, { id: "4" }, { id: "5" }]

// Technical and Fundamental sample data
export const technicalData: TechnicalData = {
  rsi: "65.5 (Neutral)",
  macd: "Bullish crossover",
  movingAverage50: "₹95.20",
  movingAverage200: "₹89.50",
  support: "₹92.00",
  resistance: "₹102.00",
}

export const fundamentalData: FundamentalData = {
  peRatio: "24.5",
  pbRatio: "3.2",
  debtToEquity: "0.45",
  currentRatio: "1.8",
  epsGrowth: "18.5% YoY",
  revenueGrowth: "22.3% YoY",
}
