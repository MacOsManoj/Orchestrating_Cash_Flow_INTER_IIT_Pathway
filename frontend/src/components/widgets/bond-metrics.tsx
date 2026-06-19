"use client"

import { useState } from "react"
import { DashboardCard } from "../ui/dashboard-card"
import { TrendingUp, TrendingDown } from "lucide-react"

const metrics = [
  { label: "Duration (Mod)", value: "7.8", trend: "up", change: "+0.2" },
  { label: "Convexity", value: "0.6", trend: "neutral", change: "0.0" },
  { label: "OAS", value: "50 bps", trend: "down", change: "-2" },
  { label: "Spread (vs UST)", value: "45 bps", trend: "down", change: "-3" },
  { label: "DV01", value: "$0.078", trend: "up", change: "+0.002" },
  { label: "Z-Spread", value: "55 bps", trend: "up", change: "+1" },
  { label: "Clean Price", value: "97.92", trend: "up", change: "+0.15" },
  { label: "Dirty Price", value: "98.75", trend: "up", change: "+0.20" },
  { label: "Amt Outstanding", value: "$50B", trend: "neutral", change: "0" },
  { label: "First Call Date", value: "N/A", trend: "neutral", change: "" },
  { label: "Issue Size", value: "$35B", trend: "neutral", change: "" },
  { label: "Settlement Date", value: "2024-02-20", trend: "neutral", change: "" },
]

export function BondMetrics() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  return (
    <DashboardCard title="Bond Metrics" className="bg-[#143432]">
      <div className="h-full space-y-3 overflow-y-auto pr-2">
        {metrics.map((metric, index) => (
          <div
            key={index}
            onMouseEnter={() => setHoveredIndex(index)}
            onMouseLeave={() => setHoveredIndex(null)}
            className={`flex items-center justify-between border-b border-[#2a3643] pb-2 transition-all ${
              hoveredIndex === index ? "bg-[#1a2530] px-2 py-1 rounded" : ""
            }`}
          >
            <span className="text-xs text-[#8a99ab]">{metric.label}</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-[#e1e7ef]">{metric.value}</span>
              {metric.trend === "up" && (
                <div className="flex items-center gap-1 text-[#00c7a5]">
                  <TrendingUp className="h-3 w-3" />
                  <span className="text-xs">{metric.change}</span>
                </div>
              )}
              {metric.trend === "down" && (
                <div className="flex items-center gap-1 text-[#e24c4c]">
                  <TrendingDown className="h-3 w-3" />
                  <span className="text-xs">{metric.change}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </DashboardCard>
  )
}
