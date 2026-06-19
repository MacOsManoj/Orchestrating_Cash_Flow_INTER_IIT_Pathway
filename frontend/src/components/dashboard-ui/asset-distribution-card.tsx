import { motion } from "framer-motion"
import { DashboardCard } from "./dashboard-card"
import { useState } from "react"

interface AssetData {
  label: string
  amount: number
}

// Sample data simulating API response (without percentage or color)
const ASSET_DISTRIBUTION_DATA: AssetData[] = [
  { label: "Stocks and derivatives", amount: 492000 },
  { label: "Bonds", amount: 307500 },
  { label: "FX", amount: 123000 },
  { label: "Commodities", amount: 307500 },
]

const COLOR_PALETTE = [
  "#E91E63", // Pink/Magenta
  "#9C27B0", // Purple
  "#14B8A6", // Teal
  "#3B82F6", // Blue
  "#F59E0B", // Amber
  "#10B981", // Green
  "#EF4444", // Red
  "#8B5CF6", // Violet
  "#EC4899", // Rose
  "#06B6D4", // Cyan
]

function processAssetData(data: AssetData[]) {
  const total = data.reduce((sum, item) => sum + item.amount, 0)

  return data.map((item, index) => ({
    ...item,
    percentage: (item.amount / total) * 100,
    color: COLOR_PALETTE[index % COLOR_PALETTE.length], // Cycle through colors
  }))
}

function formatCurrency(amount: number): string {
  if (amount >= 1_000_000) {
    return `$ ${(amount / 1_000_000).toFixed(2)} M`
  } else if (amount >= 1_000) {
    return `$ ${(amount / 1_000).toFixed(2)} K`
  }
  return `$ ${amount.toFixed(2)}`
}

export function AssetDistributionCard() {
  const [hoveredSegment, setHoveredSegment] = useState<number | null>(null)

  const processedData = processAssetData(ASSET_DISTRIBUTION_DATA)
  const totalValue = ASSET_DISTRIBUTION_DATA.reduce((sum, item) => sum + item.amount, 0)

  const radius = 60
  const circumference = 2 * Math.PI * radius

  let cumulativeOffset = 0
  const segments = processedData.map((item) => {
    const dashLength = (item.percentage / 100) * circumference
    const segment = {
      ...item,
      dashArray: `${dashLength} ${circumference}`,
      offset: -cumulativeOffset,
    }
    cumulativeOffset += dashLength
    return segment
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="lg:col-span-2"
    >
      <DashboardCard>
        <div className="flex flex-col md:flex-row items-center gap-6 h-full">
          {/* Chart */}
          <div className="relative flex-shrink-0">
            <svg width="160" height="160" viewBox="0 0 160 160" className="transform -rotate-90">
              <circle cx="80" cy="80" r="60" fill="none" stroke="#1a3a3a" strokeWidth="24" />

              {segments.map((segment, index) => (
                <g key={index}>
                  <circle
                    cx="80"
                    cy="80"
                    r="60"
                    fill="none"
                    stroke={segment.color}
                    strokeWidth="24"
                    strokeDasharray={segment.dashArray}
                    strokeDashoffset={segment.offset}
                    strokeLinecap="round"
                    className="cursor-pointer transition-opacity"
                    style={{ opacity: hoveredSegment === null || hoveredSegment === index ? 1 : 0.3 }}
                    onMouseEnter={() => setHoveredSegment(index)}
                    onMouseLeave={() => setHoveredSegment(null)}
                  />
                </g>
              ))}
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              {hoveredSegment !== null ? (
                <>
                  <p className="text-xs text-white/70 text-center px-2">{processedData[hoveredSegment].label}</p>
                  <p className="text-lg font-bold text-white">{processedData[hoveredSegment].percentage.toFixed(1)}%</p>
                </>
              ) : (
                <>
                  <p className="text-xs text-white/70">Total Value</p>
                  <p className="text-xl font-bold text-white">{formatCurrency(totalValue)}</p>
                </>
              )}
            </div>
          </div>

          {/* Legend */}
          <div className="flex-1 space-y-3">
            <h3 className="text-base font-semibold text-white mb-4">Asset distribution</h3>
            {processedData.map((item, index) => (
              <div
                key={index}
                className="flex items-center gap-3 cursor-pointer transition-opacity"
                style={{ opacity: hoveredSegment === null || hoveredSegment === index ? 1 : 0.5 }}
                onMouseEnter={() => setHoveredSegment(index)}
                onMouseLeave={() => setHoveredSegment(null)}
              >
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                <div className="flex-1">
                  <p className="text-sm text-white">{item.label}</p>
                  <p className="text-xs text-white/70">{item.percentage.toFixed(0)}%</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </DashboardCard>
    </motion.div>
  )
}
