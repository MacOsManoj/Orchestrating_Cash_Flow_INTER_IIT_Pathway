import { motion } from "framer-motion"
import { DashboardCard } from "./dashboard-card"

interface KeyMetric {
  label: string
  value: string
}

interface HoldingItem {
  id: number
  name: string
  badge: string
  exposurePercent: number
}

const KEY_METRICS_DATA: KeyMetric[] = [
  { label: "Volatility", value: "15.2%" },
  { label: "VaR (95%)", value: "-$25,310" },
  { label: "Beta", value: "1.15" },
  { label: "Expected Shortfall", value: "-$42,780" },
]

// Sample data simulating API response (without badgeColor)
const HOLDINGS_DATA: HoldingItem[] = [
  { id: 1, name: "Microsoft Corp", badge: "MS", exposurePercent: 60 },
  { id: 2, name: "Apple Inc", badge: "AP", exposurePercent: 55 },
  { id: 3, name: "Amazon", badge: "AZ", exposurePercent: 50 },
  { id: 4, name: "Tesla", badge: "TS", exposurePercent: 45 },
]

const HOLDINGS_BADGE_COLORS = [
  "#3b82f6", // Blue
  "#a855f7", // Purple
  "#14b8a6", // Teal
  "#fb923c", // Orange
  "#ec4899", // Pink
  "#10b981", // Green
  "#f59e0b", // Amber
  "#8b5cf6", // Violet
]

function processHoldingsData(data: HoldingItem[]) {
  return data.map((item, index) => ({
    ...item,
    badgeColor: HOLDINGS_BADGE_COLORS[index % HOLDINGS_BADGE_COLORS.length],
  }))
}

export function KeyMetricsCard() {
  const processedHoldings = processHoldingsData(HOLDINGS_DATA)

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
      <DashboardCard>
        <div className="flex flex-col h-full">
          <h3 className="text-base font-semibold text-white mb-6">Key metrics</h3>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            {KEY_METRICS_DATA.map((metric, index) => (
              <div key={index}>
                <p className="text-xs text-white/70 mb-1">{metric.label}</p>
                <p className="text-xl font-bold text-white">{metric.value}</p>
              </div>
            ))}
          </div>

          {/* Holdings section */}
          <div className="mt-auto">
            <h4 className="text-sm font-medium text-white mb-3">Top 5 Holdings / Counterparty Exposure %</h4>
            <div className="space-y-2">
              {processedHoldings.map((holding) => (
                <div key={holding.id} className="flex items-center gap-3">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: holding.badgeColor }}
                  >
                    <span className="text-[10px] font-bold text-white">{holding.badge}</span>
                  </div>
                  <p className="text-xs text-white flex-shrink-0 w-32">{holding.name}</p>
                  <div className="flex-1 bg-[#1a3a3a] rounded-full h-2">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        backgroundColor: holding.badgeColor,
                        width: `${holding.exposurePercent}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </DashboardCard>
    </motion.div>
  )
}
