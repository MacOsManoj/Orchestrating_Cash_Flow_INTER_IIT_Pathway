"use client"

import { useState } from "react"
import { DashboardCard } from "../components/ui/dashboard-card"
import { Button } from "../components/ui/button"
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Activity,
  BarChart3,
  Globe,
  Users,
} from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"

type TimePeriod = "1D" | "1W" | "1M" | "1Y" | "YTD"

// Generate realistic gold price data
const generatePriceData = (period: TimePeriod) => {
  const dataPoints: { [key in TimePeriod]: number } = {
    "1D": 24,
    "1W": 7,
    "1M": 30,
    "1Y": 12,
    YTD: 10,
  }

  const points = dataPoints[period]
  const basePrice = 2350
  const data = []

  for (let i = 0; i < points; i++) {
    const variance = Math.random() * 60 - 30
    const price = basePrice + variance + i * 2
    data.push({
      time: i,
      price: Number(price.toFixed(2)),
      label:
        period === "1D"
          ? `${i}:00`
          : period === "1W"
            ? ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i]
            : `P${i + 1}`,
    })
  }

  return data
}

const newsArticles = [
  {
    title: "Gold Prices Surge as Inflation Fears Mount Across Global Markets",
    source: "Reuters",
    time: "2 hours ago",
    icon: "📈",
  },
  {
    title: "Federal Reserve's Latest Statement Signals Potential Rate Cuts, Affecting Gold",
    source: "Bloomberg",
    time: "5 hours ago",
    icon: "🏛️",
  },
  {
    title: "Central Banks Increase Gold Reserves Amid Economic Uncertainty",
    source: "Financial Times",
    time: "8 hours ago",
    icon: "🌍",
  },
]

export function GoldTradingDashboard() {
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>("1D")
  const [priceData, setPriceData] = useState(generatePriceData("1D"))
  const [currentPrice, setCurrentPrice] = useState(2350.75)
  const [change, setChange] = useState(25.5)
  const [changePercent, setChangePercent] = useState(1.1)

  const handlePeriodChange = (period: TimePeriod) => {
    setSelectedPeriod(period)
    const newData = generatePriceData(period)
    setPriceData(newData)

    // Simulate price changes based on period
    const priceVariation = Math.random() * 40 - 20
    setCurrentPrice(Number((2350.75 + priceVariation).toFixed(2)))
    setChange(Number((25.5 + priceVariation / 2).toFixed(2)))
    setChangePercent(Number(((change / currentPrice) * 100).toFixed(2)))
  }

  const holdings = {
    value: 12450.0,
    percentage: 45,
    avgBuyPrice: 2150.25,
    unrealizedGL: 1120.75,
    portfolioExposure: 15.5,
  }

  const keyStats = {
    open: 2325.25,
    high: 2355.8,
    low: 2322.1,
    volume: "185.3K",
    marketCap: "$15.8T",
    weekHigh: 2449.89,
  }

  const riskMetrics = [
    { label: "Historical volatility", value: "18.5%", status: "neutral" },
    { label: "Value at Risk (VaR 95%)", value: "$1250", status: "warning" },
    { label: "Beta (vs. S&P 500)", value: "0.05", status: "good" },
    { label: "Liquidity Score", value: "98/100", status: "good" },
    { label: "Correlation matrix", value: "View Matrix", status: "link" },
  ]

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <DashboardCard className="border-teal-900/30">
        <div className="flex items-start justify-between mb-6">
          <h1 className="text-3xl font-bold text-white">Gold (XAU/USD)</h1>
          <div className="flex gap-2">
            <Button className="bg-teal-600 hover:bg-teal-700 text-white font-semibold transition-all hover:scale-105 hover:shadow-lg hover:shadow-teal-600/30">
              Buy
            </Button>
            <Button className="bg-red-600 hover:bg-red-700 text-white font-semibold transition-all hover:scale-105 hover:shadow-lg hover:shadow-red-600/30">
              Sell
            </Button>
            <Button
              variant="outline"
              className="border-teal-600 text-teal-400 hover:bg-teal-950 bg-transparent transition-all hover:border-teal-400 hover:scale-105"
            >
              Compare <ChevronDown className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Current Market Price */}
          <div className="border border-teal-900/30 rounded-lg p-4 bg-[#0a1e1e]/30 hover:bg-[#0a1e1e]/50 hover:border-teal-700/50 transition-all duration-300 cursor-pointer hover:scale-[1.02]">
            <div className="text-sm text-gray-400 mb-1">Current Market Price</div>
            <div className="text-3xl font-bold text-white mb-2">${currentPrice.toLocaleString()}</div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">24-hour Change</span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-lg font-semibold ${change >= 0 ? "text-teal-400" : "text-red-400"}`}>
                {change >= 0 ? "+" : ""}${change.toFixed(2)}
              </span>
              <span className={`text-sm flex items-center ${change >= 0 ? "text-teal-400" : "text-red-400"}`}>
                {change >= 0 ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
                {change >= 0 ? "+" : ""}
                {changePercent}%
              </span>
            </div>
          </div>

          {/* Your Holdings */}
          <div className="border border-teal-900/30 rounded-lg p-4 bg-[#0a1e1e]/30 hover:bg-[#0a1e1e]/50 hover:border-teal-700/50 transition-all duration-300 cursor-pointer hover:scale-[1.02]">
            <div className="flex justify-between items-start mb-2">
              <div className="text-sm text-gray-400">Your Holdings</div>
              <div className="text-xs text-gray-500">% of commodity</div>
            </div>
            <div className="text-3xl font-bold text-white mb-3">${holdings.value.toLocaleString()}</div>
            <div className="text-2xl font-semibold text-teal-400 mb-3">{holdings.percentage}%</div>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-gray-500 text-xs">Avg. Buy Price</div>
                <div className="text-white font-medium">${holdings.avgBuyPrice.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs">Unrealized G/L</div>
                <div className="text-teal-400 font-medium">+${holdings.unrealizedGL.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs">Portfolio Exposure</div>
                <div className="text-white font-medium">{holdings.portfolioExposure}%</div>
              </div>
            </div>
          </div>

          {/* Key Stats */}
          <div className="border border-teal-900/30 rounded-lg p-4 bg-[#0a1e1e]/30 hover:bg-[#0a1e1e]/50 hover:border-teal-700/50 transition-all duration-300 cursor-pointer hover:scale-[1.02]">
            <div className="text-sm text-gray-400 mb-3">Key Stats</div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <div className="text-gray-500 text-xs mb-1">Open</div>
                <div className="text-white font-medium">${keyStats.open.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs mb-1">High</div>
                <div className="text-white font-medium">${keyStats.high.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs mb-1">Low</div>
                <div className="text-white font-medium">${keyStats.low.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs mb-1">Volume</div>
                <div className="text-white font-medium">{keyStats.volume}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs mb-1">Market Cap</div>
                <div className="text-white font-medium">{keyStats.marketCap}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs mb-1">52 Week High</div>
                <div className="text-white font-medium">${keyStats.weekHigh.toLocaleString()}</div>
              </div>
            </div>
          </div>
        </div>
      </DashboardCard>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Price Chart */}
        <DashboardCard className="lg:col-span-2 border-teal-900/30">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Price Chart</h3>
            <div className="flex gap-2">
              {(["1D", "1W", "1M", "1Y", "YTD"] as TimePeriod[]).map((period) => (
                <button
                  key={period}
                  onClick={() => handlePeriodChange(period)}
                  className={`px-3 py-1 text-sm rounded transition-all duration-200 ${
                    selectedPeriod === period
                      ? "bg-teal-600 text-white shadow-lg shadow-teal-600/30"
                      : "text-gray-400 hover:text-white hover:bg-teal-900/30 hover:scale-105"
                  }`}
                >
                  {period}
                </button>
              ))}
            </div>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e3a3a" />
                <XAxis dataKey="label" stroke="#6b7280" style={{ fontSize: "12px" }} />
                <YAxis stroke="#6b7280" style={{ fontSize: "12px" }} domain={["dataMin - 20", "dataMax + 20"]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f2d2d",
                    border: "1px solid #14b8a6",
                    borderRadius: "8px",
                    color: "#fff",
                  }}
                  formatter={(value: number) => [`$${value.toFixed(2)}`, "Price"]}
                />
                <ReferenceLine y={currentPrice} stroke="#14b8a6" strokeDasharray="3 3" />
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#14b8a6"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: "#14b8a6" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </DashboardCard>

        {/* News and Analytics */}
        <DashboardCard className="border-teal-900/30">
          <h3 className="text-lg font-semibold text-white mb-4">News and analytics</h3>
          <div className="space-y-4">
            {newsArticles.map((article, index) => (
              <div
                key={index}
                className="flex gap-3 p-3 rounded-lg bg-[#0a1e1e]/30 hover:bg-[#0a1e1e]/60 cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:border hover:border-teal-700/30"
              >
                <div className="text-2xl">{article.icon}</div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-white mb-1 line-clamp-2">{article.title}</h4>
                  <p className="text-xs text-gray-500">
                    {article.source} • {article.time}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market Context */}
        <DashboardCard className="border-teal-900/30 hover:border-teal-700/50 transition-all duration-300">
          <h3 className="text-lg font-semibold text-white mb-4">Market Context</h3>

          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-[#0a1e1e]/30 border border-teal-900/20">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-5 w-5 text-teal-400" />
                <h4 className="text-sm font-semibold text-white">Current Trend</h4>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed">
                Gold is currently experiencing upward momentum, driven by renewed inflation concerns and geopolitical
                instability. Investors are flocking to the precious metal as a safe-haven asset during these uncertain
                times.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-[#0a1e1e]/30 border border-teal-900/20">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="h-5 w-5 text-teal-400" />
                <h4 className="text-sm font-semibold text-white">Federal Reserve Impact</h4>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed">
                The Federal Reserve's recent dovish stance has further fueled this rally, as lower interest rates
                decrease the opportunity cost of holding non-yielding bullion.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-[#0a1e1e]/30 border border-teal-900/20">
              <div className="flex items-center gap-2 mb-2">
                <Globe className="h-5 w-5 text-teal-400" />
                <h4 className="text-sm font-semibold text-white">Global Economic Factors</h4>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed">
                Central banks worldwide are increasing their gold reserves, reflecting growing concerns about currency
                devaluation and economic stability in major economies.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-[#0a1e1e]/30 border border-teal-900/20">
              <div className="flex items-center gap-2 mb-2">
                <Users className="h-5 w-5 text-teal-400" />
                <h4 className="text-sm font-semibold text-white">Market Sentiment</h4>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-400">Institutional investors are net buyers</p>
                <span className="text-sm font-semibold text-teal-400">+12.5% flows</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 mt-2">
                <div className="bg-teal-500 h-2 rounded-full" style={{ width: "72%" }} />
              </div>
              <p className="text-xs text-gray-500 mt-1">72% bullish sentiment</p>
            </div>
          </div>
        </DashboardCard>

        {/* Risk Tracking */}
        <DashboardCard className="border-teal-900/30 hover:border-teal-700/50 transition-all duration-300">
          <h3 className="text-lg font-semibold text-white mb-4">Risk Tracking</h3>
          <div className="space-y-3">
            {riskMetrics.map((metric, index) => (
              <div
                key={index}
                className="flex items-center justify-between py-2 hover:bg-[#0a1e1e]/30 px-2 rounded transition-colors"
              >
                <span className="text-sm text-gray-400">{metric.label}</span>
                <div className="flex items-center gap-2">
                  {metric.status === "warning" && <AlertTriangle className="h-4 w-4 text-yellow-500" />}
                  {metric.status === "good" && <CheckCircle2 className="h-4 w-4 text-teal-400" />}
                  <span
                    className={`text-sm font-medium ${
                      metric.status === "link" ? "text-teal-400 cursor-pointer hover:underline" : "text-white"
                    }`}
                  >
                    {metric.value}
                  </span>
                </div>
              </div>
            ))}
            <div className="mt-4 pt-4 border-t border-teal-900/30">
              <div className="flex items-start gap-2 text-sm p-2 rounded bg-yellow-500/10 hover:bg-yellow-500/20 transition-colors">
                <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <p className="text-gray-400">Market volatility is currently high.</p>
              </div>
              <div className="flex items-start gap-2 text-sm mt-2 p-2 rounded bg-red-500/10 hover:bg-red-500/20 transition-colors">
                <div className="h-4 w-4 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <div className="h-2 w-2 rounded-full bg-red-500" />
                </div>
                <p className="text-gray-400">Commodity exposed to geopolitical risks.</p>
              </div>
            </div>
          </div>
        </DashboardCard>
      </div>
    </div>
  )
}
