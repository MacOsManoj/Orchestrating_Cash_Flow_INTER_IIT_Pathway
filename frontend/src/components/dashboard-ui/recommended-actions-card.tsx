"use client"
import { motion } from "framer-motion"
import { AlertCircle, TrendingUp, Scale, type LucideIcon } from "lucide-react"
import { DashboardCard } from "./dashboard-card"

interface ActionItem {
  id: number
  icon: LucideIcon
  title: string
  description: string
  iconBg: string
  iconColor: string
}

const RECOMMENDED_ACTIONS_DATA: ActionItem[] = [
  {
    id: 1,
    icon: AlertCircle,
    title: "Sell Peloton Stock",
    description: "High volatility detected",
    iconBg: "#ef444433",
    iconColor: "#ef4444",
  },
  {
    id: 2,
    icon: TrendingUp,
    title: "Buy Azon Inc.",
    description: "Strong upward trend.",
    iconBg: "#22c55e33",
    iconColor: "#22c55e",
  },
  {
    id: 3,
    icon: Scale,
    title: "Rebalance Portfolio",
    description: "Tech sector overweight.",
    iconBg: "#14b8a633",
    iconColor: "#14b8a6",
  },
]

export function RecommendedActionsCard() {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
      <DashboardCard>
        <div className="flex flex-col h-full">
          <h3 className="text-base font-semibold text-white mb-6">Recommended Actions</h3>
          <div className="space-y-4">
            {RECOMMENDED_ACTIONS_DATA.map((action) => (
              <div key={action.id} className="flex items-center gap-4">
                <div
                  className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: action.iconBg }}
                >
                  <action.icon className="w-6 h-6" style={{ color: action.iconColor }} />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-white mb-0.5">{action.title}</h4>
                  <p className="text-xs text-white/70">{action.description}</p>
                </div>
                <button className="group relative px-3 py-1.5 sm:px-4 sm:py-2 bg-[#1a3a3a] border border-[#2a4a4a] rounded-lg text-xs sm:text-sm font-medium text-white transition-all duration-300 hover:border-accent-teal hover:bg-accent-teal/10 hover:shadow-lg hover:shadow-accent-teal/20 hover:scale-105 flex-shrink-0">
                  <span className="relative z-10">Review</span>
                  <div className="absolute inset-0 bg-gradient-to-r from-accent-teal/0 via-accent-teal/10 to-accent-teal/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-lg" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </DashboardCard>
    </motion.div>
  )
}
