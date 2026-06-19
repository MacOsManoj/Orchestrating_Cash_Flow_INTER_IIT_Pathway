"use client"

import { useState } from "react"

const periods = ["1D", "1W", "1M", "1Y", "YTD"]

export function PortfolioChart() {
  const [selectedPeriod, setSelectedPeriod] = useState("1D")

  return (
    <div className="h-full flex flex-col">
      {/* Period Selector */}
      <div className="flex gap-2 mb-6">
        {periods.map((period) => (
          <button
            key={period}
            onClick={() => setSelectedPeriod(period)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
              selectedPeriod === period
                ? "bg-accent-green-dim text-text-primary"
                : "bg-transparent text-text-muted hover:text-text-secondary"
            }`}
          >
            {period}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="flex-1 relative min-h-[300px]">
        <svg width="100%" height="100%" viewBox="0 0 600 300" preserveAspectRatio="none" className="absolute inset-0">
          {/* Grid lines */}
          <line x1="0" y1="75" x2="600" y2="75" stroke="hsl(var(--color-border))" strokeWidth="1" opacity="0.3" />
          <line x1="0" y1="150" x2="600" y2="150" stroke="hsl(var(--color-border))" strokeWidth="1" opacity="0.3" />
          <line x1="0" y1="225" x2="600" y2="225" stroke="hsl(var(--color-border))" strokeWidth="1" opacity="0.3" />

          {/* Red area (losses) */}
          <path
            d="M 0,180 L 30,185 L 50,195 L 90,200 L 130,190 L 180,210 L 220,205 L 250,220 L 600,220 L 600,300 L 0,300 Z"
            fill="hsl(var(--color-accent-red))"
            opacity="0.2"
          />
          <path
            d="M 0,180 L 30,185 L 50,195 L 90,200 L 130,190 L 180,210 L 220,205 L 250,220"
            stroke="hsl(var(--color-accent-red))"
            strokeWidth="2"
            fill="none"
          />

          {/* Green area (gains) */}
          <path
            d="M 250,220 L 280,180 L 320,120 L 360,90 L 380,70 L 420,80 L 450,50 L 480,45 L 510,60 L 540,55 L 570,65 L 600,70 L 600,300 L 250,300 Z"
            fill="hsl(var(--color-accent-green))"
            opacity="0.2"
          />
          <path
            d="M 250,220 L 280,180 L 320,120 L 360,90 L 380,70 L 420,80 L 450,50 L 480,45 L 510,60 L 540,55 L 570,65 L 600,70"
            stroke="hsl(var(--color-accent-green))"
            strokeWidth="2"
            fill="none"
          />
        </svg>
      </div>
    </div>
  )
}
