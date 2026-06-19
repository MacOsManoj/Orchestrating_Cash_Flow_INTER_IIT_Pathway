import { motion } from "framer-motion"
import { TrendingUp, Landmark, DollarSign, type LucideIcon } from "lucide-react"
import { DashboardCard } from "./dashboard-card"

interface NewsItem {
  id: number
  title: string
  time: string
  source: string
  icon: LucideIcon
  iconBg: string
  iconColor: string
}

const MARKET_NEWS_DATA: NewsItem[] = [
  {
    id: 1,
    title: "Tech stocks rally on positive inflation data",
    time: "2 hours ago",
    source: "Reuters",
    icon: TrendingUp,
    iconBg: "#14b8a633",
    iconColor: "#14b8a6",
  },
  {
    id: 2,
    title: "Oil prices surge as OPEC+ announces production cuts",
    time: "5 hours ago",
    source: "Bloomberg",
    icon: DollarSign,
    iconBg: "#3b82f633",
    iconColor: "#3b82f6",
  },
  {
    id: 3,
    title: "Federal Reserve hints at interest rate stability for Q3",
    time: "8 hours ago",
    source: "Wall Street Journal",
    icon: Landmark,
    iconBg: "#a855f733",
    iconColor: "#a855f7",
  },
]

export function MarketNewsCard() {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
      <DashboardCard>
        <div className="flex flex-col h-full">
          <h3 className="text-base font-semibold text-white mb-6">Market News</h3>
          <div className="space-y-4">
            {MARKET_NEWS_DATA.map((news) => (
              <div
                key={news.id}
                className="flex items-start gap-4 p-3 rounded-lg hover:bg-card-hover transition-colors cursor-pointer"
              >
                <div
                  className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: news.iconBg }}
                >
                  <news.icon className="w-6 h-6" style={{ color: news.iconColor }} />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-white mb-1 line-clamp-2">{news.title}</h4>
                  <p className="text-xs text-white/70">
                    {news.time} - {news.source}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </DashboardCard>
    </motion.div>
  )
}
