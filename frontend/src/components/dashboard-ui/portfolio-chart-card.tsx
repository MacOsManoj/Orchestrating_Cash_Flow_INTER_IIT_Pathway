import { motion } from "framer-motion"
import { useState } from "react"
import { DashboardCard } from "./dashboard-card"

const portfolioData = {
  "1D": {
    baseline: 12300000,
    data: [
      { time: "9:30", value: 12300000 },
      { time: "10:00", value: 12250000 },
      { time: "11:00", value: 12280000 },
      { time: "12:00", value: 12200000 },
      { time: "13:00", value: 12150000 },
      { time: "14:00", value: 12320000 },
      { time: "15:00", value: 12450000 },
      { time: "15:30", value: 12380000 },
      { time: "16:00", value: 12315000 },
    ],
  },
  "1W": {
    baseline: 12100000,
    data: [
      { time: "Mon", value: 12100000 },
      { time: "Tue", value: 12050000 },
      { time: "Wed", value: 11980000 },
      { time: "Thu", value: 12150000 },
      { time: "Fri", value: 12320000 },
    ],
  },
  "1M": {
    baseline: 11800000,
    data: [
      { time: "Wk1", value: 11800000 },
      { time: "Wk2", value: 11750000 },
      { time: "Wk3", value: 12100000 },
      { time: "Wk4", value: 12350000 },
    ],
  },
  "1Y": {
    baseline: 10500000,
    data: [
      { time: "Jan", value: 10500000 },
      { time: "Feb", value: 10800000 },
      { time: "Mar", value: 10650000 },
      { time: "Apr", value: 11200000 },
      { time: "May", value: 11500000 },
      { time: "Jun", value: 11300000 },
      { time: "Jul", value: 11650000 },
      { time: "Aug", value: 11900000 },
      { time: "Sep", value: 12100000 },
      { time: "Oct", value: 11950000 },
      { time: "Nov", value: 12350000 },
      { time: "Dec", value: 12300000 },
    ],
  },
  YTD: {
    baseline: 11800000,
    data: [
      { time: "Jan", value: 11800000 },
      { time: "Feb", value: 12000000 },
      { time: "Mar", value: 12150000 },
      { time: "Apr", value: 12300000 },
    ],
  },
}

export function PortfolioChartCard() {
  const [activePeriod, setActivePeriod] = useState<keyof typeof portfolioData>("1D")
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)
  const periods = ["1D", "1W", "1M", "1Y", "YTD"] as const

  const { baseline, data } = portfolioData[activePeriod]

  const width = 600
  const height = 300
  const padding = { top: 20, right: 20, bottom: 40, left: 20 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom

  const values = data.map((d) => d.value)
  const minValue = Math.min(...values, baseline)
  const maxValue = Math.max(...values, baseline)
  const valueRange = maxValue - minValue || 1

  const createPathSegments = () => {
    const segments: { path: string; color: string }[] = []
    let currentPath = ""
    let currentColor = ""

    data.forEach((point, index) => {
      const x = padding.left + (index / (data.length - 1)) * chartWidth
      const y = padding.top + chartHeight - ((point.value - minValue) / valueRange) * chartHeight

      // Determine color based on comparison to baseline
      const isAboveBaseline = point.value >= baseline
      const color = isAboveBaseline ? "#10B981" : "#EF4444" // green : red

      if (index === 0) {
        currentPath = `M ${x} ${y}`
        currentColor = color
      } else {
        if (color !== currentColor) {
          // Finish current segment
          segments.push({ path: currentPath, color: currentColor })
          // Start new segment from previous point
          const prevX = padding.left + ((index - 1) / (data.length - 1)) * chartWidth
          const prevY = padding.top + chartHeight - ((data[index - 1].value - minValue) / valueRange) * chartHeight
          currentPath = `M ${prevX} ${prevY} L ${x} ${y}`
          currentColor = color
        } else {
          currentPath += ` L ${x} ${y}`
        }
      }

      if (index === data.length - 1) {
        segments.push({ path: currentPath, color: currentColor })
      }
    })

    return segments
  }

  const pathSegments = createPathSegments()

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="lg:col-span-2"
    >
      <DashboardCard>
        <div className="flex flex-col h-full">
          {/* Period selector */}
          <div className="flex gap-2 mb-6">
            {periods.map((period) => (
              <button
                key={period}
                onClick={() => setActivePeriod(period)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  activePeriod === period
                    ? "bg-accent-teal text-background"
                    : "bg-transparent text-white hover:bg-accent-teal/20"
                }`}
              >
                {period}
              </button>
            ))}
          </div>

          {/* Chart */}
          <div className="flex-1 min-h-[300px] relative">
            <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
              {/* Grid lines */}
              {[0, 1, 2, 3, 4].map((i) => (
                <line
                  key={i}
                  x1={padding.left}
                  y1={padding.top + (i * chartHeight) / 4}
                  x2={width - padding.right}
                  y2={padding.top + (i * chartHeight) / 4}
                  stroke="rgba(255, 255, 255, 0.1)"
                  strokeWidth="1"
                />
              ))}

              <line
                x1={padding.left}
                y1={padding.top + chartHeight - ((baseline - minValue) / valueRange) * chartHeight}
                x2={width - padding.right}
                y2={padding.top + chartHeight - ((baseline - minValue) / valueRange) * chartHeight}
                stroke="rgba(255, 255, 255, 0.2)"
                strokeWidth="1"
                strokeDasharray="4 4"
              />

              {/* Draw path segments with appropriate colors */}
              {pathSegments.map((segment, index) => (
                <path
                  key={index}
                  d={segment.path}
                  fill="none"
                  stroke={segment.color}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              ))}

              {/* Data points with hover interaction */}
              {data.map((point, index) => {
                const x = padding.left + (index / (data.length - 1)) * chartWidth
                const y = padding.top + chartHeight - ((point.value - minValue) / valueRange) * chartHeight
                const isAboveBaseline = point.value >= baseline
                const change = point.value - baseline

                return (
                  <g key={index}>
                    {/* Invisible hover area */}
                    <circle
                      cx={x}
                      cy={y}
                      r="15"
                      fill="transparent"
                      onMouseEnter={() => setHoveredPoint(index)}
                      onMouseLeave={() => setHoveredPoint(null)}
                      style={{ cursor: "pointer" }}
                    />
                    {/* Visible point */}
                    <circle
                      cx={x}
                      cy={y}
                      r={hoveredPoint === index ? "5" : "3"}
                      fill={isAboveBaseline ? "#10B981" : "#EF4444"}
                      className="transition-all"
                      style={{ pointerEvents: "none" }}
                    />
                    {/* Tooltip */}
                    {hoveredPoint === index && (
                      <g>
                        <rect
                          x={x - 60}
                          y={y - 50}
                          width="120"
                          height="40"
                          fill="rgba(15, 36, 36, 0.95)"
                          stroke="rgba(255, 255, 255, 0.2)"
                          strokeWidth="1"
                          rx="4"
                        />
                        <text x={x} y={y - 32} textAnchor="middle" fill="white" fontSize="11" fontWeight="600">
                          ${(point.value / 1000000).toFixed(2)}M
                        </text>
                        <text
                          x={x}
                          y={y - 18}
                          textAnchor="middle"
                          fill={isAboveBaseline ? "#10B981" : "#EF4444"}
                          fontSize="10"
                          fontWeight="500"
                        >
                          {change >= 0 ? "+" : ""}${(change / 1000).toFixed(0)}K
                        </text>
                      </g>
                    )}
                  </g>
                )
              })}

              {/* X-axis labels */}
              {data.map((point, index) => {
                if (data.length > 8 && index % 2 !== 0) return null
                const x = padding.left + (index / (data.length - 1)) * chartWidth
                return (
                  <text
                    key={index}
                    x={x}
                    y={height - 10}
                    textAnchor="middle"
                    fill="rgba(255, 255, 255, 0.5)"
                    fontSize="10"
                  >
                    {point.time}
                  </text>
                )
              })}
            </svg>
          </div>
        </div>
      </DashboardCard>
    </motion.div>
  )
}
