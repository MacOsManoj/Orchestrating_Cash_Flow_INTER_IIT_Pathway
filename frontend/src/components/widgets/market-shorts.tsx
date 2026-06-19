"use client"

import { useState } from "react"
import { DashboardCard } from "../ui/dashboard-card"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

const metrics = [
  {
    label: "Short Interest",
    value: "2.1%",
    trend: "up",
    change: "+0.3%",
    description: "Percentage of shares sold short",
  },
  {
    label: "Days to Cover",
    value: "3.5",
    trend: "down",
    change: "-0.5",
    description: "Days to cover all short positions",
  },
  { label: "Borrow Rate", value: "0.8%", trend: "up", change: "+0.1%", description: "Cost to borrow shares" },
  { label: "Short Volume", value: "150K", trend: "up", change: "+15K", description: "Recent short volume" },
  {
    label: "Average Daily Volume",
    value: "2.5M",
    trend: "neutral",
    change: "0",
    description: "Average daily trading volume",
  },
  {
    label: "Short % of Float",
    value: "0.7%",
    trend: "down",
    change: "-0.1%",
    description: "Short interest as % of float",
  },
  {
    label: "Sentiment (past 7d)",
    value: "Bearish",
    color: "text-[#e00618]",
    trend: "down",
    change: "",
    description: "Market sentiment indicator",
  },
]

export function MarketShorts() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  return (
    <DashboardCard title="Market Shorts" className="bg-[#143432]">
      <div className="h-full space-y-3 overflow-y-auto pr-2">
        {metrics.map((metric, index) => (
          <div
            key={index}
            onMouseEnter={() => setHoveredIndex(index)}
            onMouseLeave={() => setHoveredIndex(null)}
            className={`relative flex items-center justify-between border-b border-[#2a3643] pb-2 transition-all ${
              hoveredIndex === index ? "bg-[#1a2530] px-2 py-1 rounded" : ""
            }`}
          >
            <span className="text-xs text-[#8a99ab]">{metric.label}</span>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${metric.color || "text-[#e1e7ef]"}`}>{metric.value}</span>
              {metric.trend === "up" && (
                <div className="flex items-center gap-1 text-[#e24c4c]">
                  <TrendingUp className="h-3 w-3" />
                  <span className="text-xs">{metric.change}</span>
                </div>
              )}
              {metric.trend === "down" && (
                <div className="flex items-center gap-1 text-[#00c7a5]">
                  <TrendingDown className="h-3 w-3" />
                  <span className="text-xs">{metric.change}</span>
                </div>
              )}
              {metric.trend === "neutral" && (
                <div className="flex items-center gap-1 text-[#8a99ab]">
                  <Minus className="h-3 w-3" />
                </div>
              )}
            </div>
            {hoveredIndex === index && (
              <div className="absolute right-0 top-full z-10 mt-1 w-48 rounded-lg border border-[#2a3643] bg-[#161e27] p-2 text-xs text-[#8a99ab] shadow-lg">
                {metric.description}
              </div>
            )}
          </div>
        ))}
      </div>
    </DashboardCard>
  )
}
