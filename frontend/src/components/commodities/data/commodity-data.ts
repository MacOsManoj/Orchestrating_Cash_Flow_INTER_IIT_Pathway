export const commodityData = {
  symbol: "XAU/USD",
  name: "Gold",

  marketPrice: {
    currentPrice: 2350.75,
    change24h: {
      value: 25.5,
      percentage: 1.1,
      isPositive: true,
    },
  },

  holdings: {
    totalValue: 12450.0,
    percentOfCommodity: 45,
    avgBuyPrice: 2150.25,
    unrealizedGainLoss: {
      value: 1120.75,
      isPositive: true,
    },
    portfolioExposure: 15.5,
  },

  keyStats: {
    open: 2325.25,
    high: 2355.8,
    low: 2322.1,
    volume: "185.3K",
    marketCap: "$15.8T",
    weekHigh52: 2449.89,
  },

  chartData: {
    timeRanges: ["1D", "1W", "1M", "1Y", "YTD"],
    defaultRange: "1D",
    // Simplified chart data points
    dataPoints: [
      { time: "00:00", price: 2325, isPositive: false },
      { time: "04:00", price: 2310, isPositive: false },
      { time: "08:00", price: 2340, isPositive: true },
      { time: "12:00", price: 2360, isPositive: true },
      { time: "16:00", price: 2450, isPositive: true },
      { time: "20:00", price: 2420, isPositive: true },
      { time: "24:00", price: 2350, isPositive: true },
    ],
    dataByRange: {
      "1D": [
        { time: "00:00", price: 2325, isPositive: false },
        { time: "04:00", price: 2310, isPositive: false },
        { time: "06:00", price: 2305, isPositive: false },
        { time: "08:00", price: 2340, isPositive: true },
        { time: "10:00", price: 2345, isPositive: true },
        { time: "12:00", price: 2360, isPositive: true },
        { time: "14:00", price: 2455, isPositive: true },
        { time: "16:00", price: 2450, isPositive: true },
        { time: "18:00", price: 2430, isPositive: true },
        { time: "20:00", price: 2420, isPositive: true },
        { time: "22:00", price: 2400, isPositive: true },
        { time: "24:00", price: 2350, isPositive: true },
      ],
      "1W": [
        { time: "Mon", price: 2280, isPositive: false },
        { time: "Tue", price: 2265, isPositive: false },
        { time: "Wed", price: 2290, isPositive: true },
        { time: "Thu", price: 2320, isPositive: true },
        { time: "Fri", price: 2380, isPositive: true },
        { time: "Sat", price: 2365, isPositive: true },
        { time: "Sun", price: 2350, isPositive: true },
      ],
      "1M": [
        { time: "Week 1", price: 2180, isPositive: false },
        { time: "Week 2", price: 2150, isPositive: false },
        { time: "Week 3", price: 2200, isPositive: true },
        { time: "Week 4", price: 2280, isPositive: true },
        { time: "Week 5", price: 2350, isPositive: true },
      ],
      "1Y": [
        { time: "Jan", price: 1850, isPositive: false },
        { time: "Feb", price: 1820, isPositive: false },
        { time: "Mar", price: 1900, isPositive: false },
        { time: "Apr", price: 1950, isPositive: true },
        { time: "May", price: 2000, isPositive: true },
        { time: "Jun", price: 2080, isPositive: true },
        { time: "Jul", price: 2150, isPositive: true },
        { time: "Aug", price: 2200, isPositive: true },
        { time: "Sep", price: 2280, isPositive: true },
        { time: "Oct", price: 2350, isPositive: true },
        { time: "Nov", price: 2420, isPositive: true },
        { time: "Dec", price: 2350, isPositive: true },
      ],
      YTD: [
        { time: "Jan", price: 2050, isPositive: false },
        { time: "Feb", price: 2020, isPositive: false },
        { time: "Mar", price: 2100, isPositive: true },
        { time: "Apr", price: 2150, isPositive: true },
        { time: "May", price: 2200, isPositive: true },
        { time: "Jun", price: 2280, isPositive: true },
        { time: "Jul", price: 2320, isPositive: true },
        { time: "Aug", price: 2380, isPositive: true },
        { time: "Sep", price: 2420, isPositive: true },
        { time: "Oct", price: 2450, isPositive: true },
        { time: "Nov", price: 2400, isPositive: true },
        { time: "Dec", price: 2350, isPositive: true },
      ],
    },
  },

  news: [
    {
      id: "1",
      title: "Gold Prices Surge as Inflation Fears Mount Across Global Markets",
      source: "Reuters",
      time: "2 hours ago",
      icon: "chart",
    },
    {
      id: "2",
      title: "Federal Reserve's Latest Statement Signals Potential Rate Cuts, Affecting Gold",
      source: "Bloomberg",
      time: "5 hours ago",
      icon: "building",
    },
  ],

  marketContext:
    "Gold is currently experiencing upward momentum, driven by renewed inflation concerns and geopolitical instability. Investors are flocking to the precious metal as a safe-haven asset, pushing prices to near all-time highs. The Federal Reserve's recent dovish stance has further fueled this rally, as lower interest rates decrease the opportunity cost of holding non-yielding bullion.",

  riskTracking: {
    historicalVolatility: 18.5,
    valueAtRisk: 1250,
    beta: 0.05,
    liquidityScore: 98,
    warnings: [
      {
        type: "high-volatility",
        message: "Market volatility is currently high.",
      },
      {
        type: "geopolitical",
        message: "Commodity exposed to geopolitical risks.",
      },
    ],
  },
}
