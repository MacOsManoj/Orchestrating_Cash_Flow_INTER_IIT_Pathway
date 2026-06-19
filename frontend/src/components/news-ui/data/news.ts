
export type RiskLevel = "Low" | "Medium" | "High"

export type RiskType = "Market Risk" | "Volatility Risk" | "Operational Risk" | "Regulatory Risk"

export interface RiskBadge {
  type: RiskType
  level: RiskLevel
}

export interface StockTicker {
  symbol: string
  shortSymbol: string
}

export interface PortfolioNewsItem {
  id: string
  source: string
  timeAgo: string
  title: string
  imageUrl: string
  ticker: StockTicker
  risks: RiskBadge[]
  url?: string
}

export interface GeneralNewsItem {
  id: string
  source: string
  timeAgo: string
  title: string
  description: string
  imageUrl: string
  sentiment: "Bullish" | "Bearish" | "Neutral"
  category: "Tech" | "Finance" | "Energy" | "All"
}

export interface TrendingTopic {
  id: string
  label: string
  trend: "up" | "down"
  icon?: string  // Emoji or icon identifier for the company/sector
  count?: number // Number of mentions
}

export interface WatchlistNewsItem {
  id: string
  ticker: string
  headline: string
  source: string
  timeAgo: string
  url?: string
}

export interface DailyBriefing {
  title: string
  subtitle: string
  thumbnailUrl: string
  captionsUrl?: string
}

export interface NewsData {
  portfolioNews: PortfolioNewsItem[]
  generalNews: GeneralNewsItem[]
  trendingTopics: TrendingTopic[]
  watchlistNews: WatchlistNewsItem[]
  dailyBriefing: DailyBriefing
}





