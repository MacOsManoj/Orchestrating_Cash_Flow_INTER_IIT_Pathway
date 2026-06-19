"use client"

import { useState } from "react"
import { DashboardCard } from "../ui/dashboard-card"
import { TrendingUp, TrendingDown } from "lucide-react"

const bonds = [
  {
    name: "US T-Bond 2.25% 2045",
    cusip: "912810SL1",
    yield: "2.85%",
    yieldChange: "+0.05%",
    yieldTrend: "up",
    price: "95.50",
    priceChange: "-0.25",
    priceTrend: "down",
    rating: "AAA",
  },
  {
    name: "US T-Bond 3.00% 2044",
    cusip: "912810SG0",
    yield: "2.81%",
    yieldChange: "-0.02%",
    yieldTrend: "down",
    price: "101.75",
    priceChange: "+0.50",
    priceTrend: "up",
    rating: "AAA",
  },
  {
    name: "US T-Bond 2.5% 2046",
    cusip: "912810SM9",
    yield: "2.88%",
    yieldChange: "+0.03%",
    yieldTrend: "up",
    price: "96.25",
    priceChange: "-0.15",
    priceTrend: "down",
    rating: "AAA",
  },
]

export function ComparativeInsights() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  return (
    <DashboardCard title="Comparative Insights" className="bg-[#143432]"> 
      <div className="h-full space-y-3 overflow-y-auto pr-2">
        {bonds.map((bond, index) => (
          <div
            key={index}
            onMouseEnter={() => setHoveredIndex(index)}
            onMouseLeave={() => setHoveredIndex(null)}
            onClick={() => setSelectedIndex(selectedIndex === index ? null : index)}
            className={`cursor-pointer rounded-lg border p-3 transition-all ${
              selectedIndex === index
                ? "border-[#00c7a5] bg-[#0f2424] shadow-lg"
                : hoveredIndex === index
                  ? "border-[#2a3643] bg-[#1a2530]"
                  : "border-[#2a3643] bg-[#0f2424]"
            }`}
          >
            <p className="mb-1 text-xs font-semibold text-[#00c7a5]">{bond.name}</p>
            <p className="mb-2 text-xs text-[#8a99ab]">CUSIP: {bond.cusip}</p>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <p className="text-[#8a99ab]">Yield</p>
                <div className="flex items-center gap-1">
                  <p className="font-semibold text-[#e1e7ef]">{bond.yield}</p>
                  {bond.yieldTrend === "up" ? (
                    <TrendingUp className="h-3 w-3 text-[#e24c4c]" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-[#00c7a5]" />
                  )}
                </div>
                <p className={`text-xs ${bond.yieldTrend === "up" ? "text-[#e24c4c]" : "text-[#00c7a5]"}`}>
                  {bond.yieldChange}
                </p>
              </div>
              <div>
                <p className="text-[#8a99ab]">Price</p>
                <div className="flex items-center gap-1">
                  <p className="font-semibold text-[#e1e7ef]">{bond.price}</p>
                  {bond.priceTrend === "up" ? (
                    <TrendingUp className="h-3 w-3 text-[#00c7a5]" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-[#e24c4c]" />
                  )}
                </div>
                <p className={`text-xs ${bond.priceTrend === "up" ? "text-[#00c7a5]" : "text-[#e24c4c]"}`}>
                  {bond.priceChange}
                </p>
              </div>
              <div>
                <p className="text-[#8a99ab]">Rating</p>
                <p className="font-semibold text-[#e1e7ef]">{bond.rating}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </DashboardCard>
  )
}
