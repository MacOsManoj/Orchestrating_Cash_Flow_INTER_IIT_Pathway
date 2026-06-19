"use client"

import { TrendingUp, Droplet, Building2 } from "lucide-react"
import { newsItems, type NewsItem } from "../data/options-data/stockData"

interface NewsCardProps {
  item: NewsItem
}

function NewsIcon({ type }: { type: NewsItem["iconType"] }) {
  const iconClass = "h-8 w-8"

  switch (type) {
    case "chart":
      return (
        <div className="flex-shrink-0 w-12 h-12 bg-teal-900/30 rounded flex items-center justify-center">
          <TrendingUp className={`${iconClass} text-teal-400`} />
        </div>
      )
    case "oil":
      return (
        <div className="flex-shrink-0 w-12 h-12 bg-teal-900/30 rounded flex items-center justify-center">
          <Droplet className={`${iconClass} text-teal-400`} />
        </div>
      )
    case "bank":
      return (
        <div className="flex-shrink-0 w-12 h-12 bg-teal-900/30 rounded flex items-center justify-center">
          <Building2 className={`${iconClass} text-teal-400`} />
        </div>
      )
  }
}

function NewsCard({ item }: NewsCardProps) {
  return (
    <div className="flex items-start gap-4 p-4 hover:bg-teal-950/20 rounded-lg transition-colors cursor-pointer">
      <NewsIcon type={item.iconType} />

      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-white mb-1 line-clamp-2">{item.title}</h4>
        <p className="text-xs text-teal-400/70">
          {item.timeAgo} - {item.source}
        </p>
      </div>
    </div>
  )
}

export function NewsAnalytics() {
  return (
    <div className="bg-[#143432]/40 border border-teal-900/40 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">News and analytics</h3>

      <div className="space-y-2">
        {newsItems.map((item) => (
          <NewsCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  )
}
