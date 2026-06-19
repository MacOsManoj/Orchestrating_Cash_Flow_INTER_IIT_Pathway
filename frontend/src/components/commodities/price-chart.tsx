"use client"

import { useState } from "react"
import { Button } from "../ui/button"

interface ChartDataPoint {
  time: string
  price: number
  isPositive: boolean
}

interface ChartData {
  timeRanges: string[]
  defaultRange: string
  dataPoints: ChartDataPoint[]
  dataByRange: {
    [key: string]: ChartDataPoint[]
  }
}

interface PriceChartProps {
  data: ChartData
}

export function PriceChart({ data }: PriceChartProps) {
  const [selectedRange, setSelectedRange] = useState(data.defaultRange)

  const currentData = data.dataByRange[selectedRange] || data.dataPoints

  // Normalize data for rendering
  const prices = currentData.map((d) => d.price)
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceRange = maxPrice - minPrice

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      {/* Time Range Buttons */}
      <div className="flex items-center gap-2 mb-6">
        {data.timeRanges.map((range) => (
          <Button
            key={range}
            onClick={() => setSelectedRange(range)}
            className={`h-8 px-3 text-xs rounded ${
              selectedRange === range
                ? "bg-primary text-white hover:bg-primary/80"
                : "bg-transparent text-muted-foreground hover:bg-card"
            }`}
          >
            {range}
          </Button>
        ))}
      </div>

      {/* SVG Chart */}
      <div className="relative h-64">
        <svg className="w-full h-full" viewBox="0 0 600 250" preserveAspectRatio="none">
          {/* Draw path */}
          <path
            d={currentData
              .map((point, index) => {
                const x = (index / (currentData.length - 1)) * 600
                const y = 250 - ((point.price - minPrice) / priceRange) * 230
                return `${index === 0 ? "M" : "L"} ${x} ${y}`
              })
              .join(" ")}
            fill="none"
            stroke={currentData[currentData.length - 1].isPositive ? "#22c55e" : "#ef4444"}
            strokeWidth="2"
          />

          {/* Color segments */}
          {currentData.map((point, index) => {
            if (index === currentData.length - 1) return null
            const nextPoint = currentData[index + 1]
            const x1 = (index / (currentData.length - 1)) * 600
            const y1 = 250 - ((point.price - minPrice) / priceRange) * 230
            const x2 = ((index + 1) / (currentData.length - 1)) * 600
            const y2 = 250 - ((nextPoint.price - minPrice) / priceRange) * 230

            return (
              <line
                key={index}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={point.isPositive ? "#22c55e" : "#ef4444"}
                strokeWidth="2"
              />
            )
          })}
        </svg>
      </div>
    </div>
  )
}
