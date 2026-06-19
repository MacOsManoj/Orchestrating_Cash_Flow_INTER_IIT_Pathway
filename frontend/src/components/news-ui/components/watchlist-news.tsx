"use client"

import type React from "react"

import { useState } from "react"
import type { WatchlistNewsItem } from "../data/news"
import { ChevronRight, Bell, BellOff } from "lucide-react"

interface WatchlistNewsProps {
  items: WatchlistNewsItem[]
  onItemClick?: (item: WatchlistNewsItem) => void
  onToggleAlert?: (item: WatchlistNewsItem) => void
}

export function WatchlistNews({ items, onItemClick, onToggleAlert }: WatchlistNewsProps) {
  const [alerts, setAlerts] = useState<Set<string>>(new Set())
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)

  const handleToggleAlert = (e: React.MouseEvent, item: WatchlistNewsItem) => {
    e.stopPropagation()
    const newAlerts = new Set(alerts)
    if (newAlerts.has(item.id)) {
      newAlerts.delete(item.id)
    } else {
      newAlerts.add(item.id)
    }
    setAlerts(newAlerts)
    onToggleAlert?.(item)
  }

  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <h3 className="text-white font-semibold text-lg mb-4">Watchlist News</h3>
      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className={`p-2 rounded-lg cursor-pointer transition-all duration-200 group
              ${hoveredItem === item.id ? "bg-white/5" : ""}`}
            onMouseEnter={() => setHoveredItem(item.id)}
            onMouseLeave={() => setHoveredItem(null)}
            onClick={() => onItemClick?.(item)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="text-white font-medium">
                  <span className="text-primary hover:text-primary/80 transition-colors">{item.ticker}:</span>{" "}
                  {item.headline}
                </div>
                <div className="text-white/70 text-sm">
                  {item.source} - {item.timeAgo}
                </div>
              </div>
              <div className="flex items-center gap-1">
                {/* <button
                  onClick={(e) => handleToggleAlert(e, item)}
                  className={`p-1 rounded-full transition-all duration-200 ${
                    alerts.has(item.id)
                      ? "bg-primary  text-white"
                      : hoveredItem === item.id
                        ? "bg-white/10 text-white/70"
                        : "opacity-0"
                  }`}
                >
                  {alerts.has(item.id) ? <Bell className="w-3.5 h-3.5" /> : <BellOff className="w-3.5 h-3.5" />}
                </button> */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (item.url) {
                      window.open(item.url, "_blank", "noopener,noreferrer");
                    }
                  }}
                  className="p-1 rounded-full hover:bg-white/10 transition-all duration-200"
                  title={item.url ? "Open article" : "No URL available"}
                  disabled={!item.url}
                >
                  <ChevronRight
                    className={`w-4 h-4 text-white/70 transition-all duration-200 ${
                      hoveredItem === item.id ? "translate-x-1 text-primary" : ""
                    } ${!item.url ? "opacity-50" : ""}`}
                  />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
