import type { NewsData } from "./news";

export const newsData: NewsData = {
  portfolioNews: [
    {
      id: "1",
      source: "Reuters",
      timeAgo: "2 hours ago",
      title: "Tech Giant Announces Breakthrough in AI, Stock Soars",
      imageUrl: "/ai-technology-chip-blue-glow.jpg",
      ticker: { symbol: "$AAPL", shortSymbol: "$A" },
      risks: [
        { type: "Market Risk", level: "Low" },
        { type: "Volatility Risk", level: "High" },
      ],
    },
    {
      id: "2",
      source: "WSJ",
      timeAgo: "8 hours ago",
      title: "EV Maker Exceeds Delivery Estimates, Shares Jump",
      imageUrl: "/electric-car-tesla-dark.jpg",
      ticker: { symbol: "$TSLA", shortSymbol: "$T" },
      risks: [
        { type: "Operational Risk", level: "Low" },
        { type: "Regulatory Risk", level: "Medium" },
      ],
    },
  ],
  generalNews: [
    {
      id: "1",
      source: "Bloomberg",
      timeAgo: "5 hours ago",
      title: "Federal Reserve Signals Potential Rate Cuts Amid Economic Slowdown",
      description:
        "In a recent statement, officials hinted at a more dovish stance, leading to a rally in bond markets and speculation among investors.",
      imageUrl: "/federal-reserve-building.png",
      sentiment: "Bearish",
      category: "Finance",
    },
  ],
  trendingTopics: [
    { id: "1", label: "#AIInnovation", trend: "up" },
    { id: "2", label: "$NVDA Earnings", trend: "up" },
    { id: "3", label: "#OilPrices", trend: "down" },
  ],
  watchlistNews: [
    {
      id: "1",
      ticker: "$GOOGL",
      headline: "Unveils new cloud computing features.",
      source: "TechCrunch",
      timeAgo: "1h ago",
    },
    {
      id: "2",
      ticker: "$MSFT",
      headline: "Secures major government contract for software solutions.",
      source: "Reuters",
      timeAgo: "3h ago",
    },
    {
      id: "3",
      ticker: "$AMZN",
      headline: "Announces expansion into new international markets.",
      source: "CNBC",
      timeAgo: "6h ago",
    },
  ],
  dailyBriefing: {
    title: "Market Summary: Tech Surges, Fed Hints",
    subtitle: "Today's top stories in 2 minutes.",
    thumbnailUrl: "/stock-market-chart-green.png",
  },
}


