import { motion } from "framer-motion"
import { DashboardCard } from "./dashboard-card"

interface PerformanceItem {
  id: number
  name: string
  category: string
  changePercent: number
  value: string
  badge: string
}

// Sample data simulating API response (without badgeColor)
const BEST_PERFORMING_DATA: PerformanceItem[] = [
  {
    id: 1,
    name: "NVD Corp",
    category: "Tech",
    changePercent: 12.5,
    value: "$2,090.45",
    badge: "NV",
  },
  {
    id: 2,
    name: "Azon Inc.",
    category: "E-commerce",
    changePercent: 8.2,
    value: "$1,750.10",
    badge: "AZ",
  },
  {
    id: 3,
    name: "BitCoin",
    category: "Crypto",
    changePercent: -2.3,
    value: "$88,345.00",
    badge: "BT",
  },
]

const BADGE_COLORS = [
  "#14b8a6", // Teal
  "#a855f7", // Purple
  "#fb923c", // Orange
  "#3b82f6", // Blue
  "#ec4899", // Pink
  "#10b981", // Green
  "#f59e0b", // Amber
  "#8b5cf6", // Violet
]

function processPerformanceData(data: PerformanceItem[]) {
  return data.map((item, index) => ({
    ...item,
    badgeColor: BADGE_COLORS[index % BADGE_COLORS.length],
    change: item.changePercent > 0 ? `+${item.changePercent}%` : `${item.changePercent}%`,
    changeColor: item.changePercent > 0 ? "#10b981" : "#ef4444", // Green for positive, red for negative
  }))
}

export function BestPerformingCard() {
  const processedData = processPerformanceData(BEST_PERFORMING_DATA)

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
      <DashboardCard>
        <div className="flex flex-col h-full">
          <h3 className="text-base font-semibold text-white mb-4">Best performing</h3>
          <div className="space-y-3">
            {processedData.map((item) => (
              <div key={item.id} className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: item.badgeColor }}
                >
                  <span className="text-xs font-bold text-white">{item.badge}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{item.name}</p>
                  <p className="text-xs text-white/70">{item.category}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold" style={{ color: item.changeColor }}>
                    {item.change}
                  </p>
                  <p className="text-xs text-white/70">{item.value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </DashboardCard>
    </motion.div>
  )
}
