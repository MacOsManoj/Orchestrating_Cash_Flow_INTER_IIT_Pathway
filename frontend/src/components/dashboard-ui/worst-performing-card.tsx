"use client"
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
const WORST_PERFORMING_DATA: PerformanceItem[] = [
  {
    id: 1,
    name: "Peloton",
    category: "Fitness",
    changePercent: -7.1,
    value: "$4.50",
    badge: "PL",
  },
  {
    id: 2,
    name: "Boeing Co",
    category: "Aerospace",
    changePercent: -4.3,
    value: "$178.20",
    badge: "BO",
  },
  {
    id: 3,
    name: "Zoom Video",
    category: "SaaS",
    changePercent: 1.5,
    value: "$65.80",
    badge: "ZO",
  },
]

const BADGE_COLORS = [
  "#ec4899", // Pink
  "#3b82f6", // Blue
  "#14b8a6", // Teal
  "#a855f7", // Purple
  "#fb923c", // Orange
  "#10b981", // Green
  "#f59e0b", // Amber
  "#8b5cf6", // Violet
]

function processPerformanceData(data: PerformanceItem[]) {
  return data.map((item, index) => ({
    ...item,
    badgeColor: BADGE_COLORS[index % BADGE_COLORS.length],
    change: item.changePercent > 0 ? `+${item.changePercent}%` : `${item.changePercent}%`,
    changeColor: item.changePercent < 0 ? "#ef4444" : "#10b981", // Red for negative, green for positive
  }))
}

export function WorstPerformingCard() {
  const processedData = processPerformanceData(WORST_PERFORMING_DATA)

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
      <DashboardCard>
        <div className="flex flex-col h-full">
          <h3 className="text-base font-semibold text-white mb-4">Worst performing</h3>
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
