export interface StockInfo {
  ticker: string
  companyName: string
  spotPrice: number
  impliedVolatility: number
  volume: string
  holdingsPercent: number
  lastUpdated: string
}

export interface OptionChainRow {
  strike: number
  ask: number
  volume: string
  openInterest: string
  iv: string
  delta: number
  isHighlighted?: boolean
}

export interface GreeksData {
  delta: number
  gamma: number
  theta: number
  vega: number
}

export interface MarketSentiment {
  putCallRatio: number
  volumeSpike: string
  ivRank: string
}

export interface NewsItem {
  id: string
  title: string
  source: string
  timeAgo: string
  iconType: "chart" | "oil" | "bank"
}

export interface PayoffPosition {
  type: "Long Call" | "Long Put" | "Short Call" | "Short Put"
  strike: number
  premium: number
  maxProfit: string
  maxLoss: string
  breakEven: number
}

export const stockInfo: StockInfo = {
  ticker: "AAPL",
  companyName: "Apple Inc.",
  spotPrice: 172.5,
  impliedVolatility: 28.5,
  volume: "1.2M",
  holdingsPercent: 20,
  lastUpdated: "10:45:32 AM EST",
}

export const optionChainData: OptionChainRow[] = [
  { strike: 10, ask: 5.65, volume: "3.1K", openInterest: "18.9K", iv: "30.5%", delta: 0.76 },
  { strike: 5, ask: 3.8, volume: "5.8K", openInterest: "35.2K", iv: "28.9%", delta: 0.64 },
  { strike: 0, ask: 2.25, volume: "4.2K", openInterest: "28.4K", iv: "27.0%", delta: 0.5, isHighlighted: true },
  { strike: 3, ask: 1.2, volume: "3.9K", openInterest: "25.1K", iv: "25.8%", delta: 0.36 },
  { strike: 0, ask: 0.65, volume: "2.8K", openInterest: "19.8K", iv: "24.9%", delta: 0.24 },
]

export const greeksData: GreeksData = {
  delta: 0.52,
  gamma: 0.08,
  theta: -0.05,
  vega: 0.12,
}

export const marketSentiment: MarketSentiment = {
  putCallRatio: 0.78,
  volumeSpike: "200 C @ 14:30",
  ivRank: "65%",
}

export const newsItems: NewsItem[] = [
  {
    id: "1",
    title: "Tech stocks rally on positive inflation data",
    source: "Reuters",
    timeAgo: "2 hours ago",
    iconType: "chart",
  },
  {
    id: "2",
    title: "Oil prices surge as OPEC+ announces production cuts",
    source: "Bloomberg",
    timeAgo: "5 hours ago",
    iconType: "oil",
  },
  {
    id: "3",
    title: "Federal Reserve hints at interest rate stability for Q3",
    source: "Wall Street Journal",
    timeAgo: "8 hours ago",
    iconType: "bank",
  },
]

export const payoffPosition: PayoffPosition = {
  type: "Long Call",
  strike: 175.0,
  premium: 1.25,
  maxProfit: "Unlimited",
  maxLoss: "$-125",
  breakEven: 176.25,
}
