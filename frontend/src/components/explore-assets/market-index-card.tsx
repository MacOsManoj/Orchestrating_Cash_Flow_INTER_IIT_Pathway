"use client"

import { useState } from "react"
import type { MarketIndex } from "../explore-assets/data/types"
import { TrendingUp, TrendingDown } from "lucide-react"

interface MarketIndexCardProps {
  index: MarketIndex
  onClick?: (index: MarketIndex) => void
}

export function MarketIndexCard({ index, onClick }: MarketIndexCardProps) {
  const [isHovered, setIsHovered] = useState(false)
  const isPositive = index.trend === "up"

  return (
    <div
      className={`
        bg-[#0f1a24] border border-[#1e3a5f] rounded-lg p-4 
        flex items-center justify-between cursor-pointer
        transition-all duration-200
        ${isHovered ? "border-primary/50 bg-[#132636] scale-[1.02]" : ""}
      `}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onClick?.(index)}
    >
      <div>
        <p className="text-muted-foreground text-sm">{index.name}</p>
        <p className="text-white text-2xl font-bold mt-1">
          {index.value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
        </p>
        <div className={`flex items-center gap-1 mt-1 text-sm ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
          {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>
            {isPositive ? "+" : ""}
            {index.change.toFixed(2)} ({index.changePercent.toFixed(2)}%)
          </span>
        </div>
      </div>
      <div className="w-20 h-12">
        <MiniChart data={index.chartData} trend={index.trend} isHovered={isHovered} />
      </div>
    </div>
  )
}

function MiniChart({ data, trend, isHovered }: { data: number[]; trend: "up" | "down"; isHovered: boolean }) {
  const isUp = trend === "up"
  const color = isUp ? "#10b981" : "#ef4444"

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const width = 80
  const height = 48
  const padding = 4

  if (isUp) {
    // Line chart for uptrend
    const points = data
      .map((value, i) => {
        const x = padding + (i / (data.length - 1)) * (width - padding * 2)
        const y = height - padding - ((value - min) / range) * (height - padding * 2)
        return `${x},${y}`
      })
      .join(" ")

    const areaPoints = `${padding},${height - padding} ${points} ${width - padding},${height - padding}`

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
        <defs>
          <linearGradient id={`gradient-${trend}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity={isHovered ? 0.4 : 0.2} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <polygon points={areaPoints} fill={`url(#gradient-${trend})`} className="transition-opacity duration-200" />
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth={isHovered ? 2.5 : 2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="transition-all duration-200"
        />
      </svg>
    )
  } else {
    // Bar chart for downtrend
    const barWidth = (width - padding * 2) / data.length - 2

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
        {data.map((value, i) => {
          const barHeight = ((value - min) / range) * (height - padding * 2) + 8
          const x = padding + i * ((width - padding * 2) / data.length) + 1
          const y = height - padding - barHeight

          return (
            <rect
              key={i}
              x={x}
              y={y}
              width={barWidth}
              height={barHeight}
              fill={color}
              opacity={isHovered ? 0.9 : 0.7}
              rx={1}
              className="transition-opacity duration-200"
            />
          )
        })}
      </svg>
    )
  }
}
