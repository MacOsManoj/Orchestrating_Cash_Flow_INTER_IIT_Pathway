"use client"

import type React from "react"

import { useState } from "react"
import type { PortfolioNewsItem } from "../data/news"
import { RiskBadge } from "./risk-badge"
import { Bookmark, ExternalLink } from "lucide-react"

interface PortfolioNewsCardProps {
  item: PortfolioNewsItem
  onBookmark?: (id: string) => void
  onClick?: (item: PortfolioNewsItem) => void
}

export function PortfolioNewsCard({ item, onBookmark, onClick }: PortfolioNewsCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsBookmarked(!isBookmarked)
    onBookmark?.(item.id)
  }

  return (
    <div
      className={`bg-card rounded-xl p-4 flex gap-4 border border-border cursor-pointer
        transition-all duration-300 ease-out
        ${isHovered ? "bg-card border-primary/50 shadow-lg shadow-primary/10 -translate-y-1" : ""}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onClick?.(item)}
    >
      <div className="relative w-32 h-24 rounded-lg overflow-hidden flex-shrink-0">
        <img
          src={item.imageUrl || "/placeholder.svg"}
          alt={item.title}
          className={`w-full h-full object-cover transition-transform duration-500 ${isHovered ? "scale-110" : ""}`}
        />
      </div>
      <div className="flex flex-col gap-2 flex-1">
        <div className="flex items-center justify-between">
          <div className="text-white/70 text-sm">
            {item.source} - {item.timeAgo}
          </div>
          <div className={`flex gap-2 transition-opacity duration-200 ${isHovered ? "opacity-100" : "opacity-0"}`}>
            <button
              onClick={handleBookmark}
              className={`p-1.5 rounded-full transition-colors ${
                isBookmarked ? "bg-primary text-white" : "bg-white/10 text-white/70 hover:text-white"
              }`}
            >
              <Bookmark className={`w-4 h-4 ${isBookmarked ? "fill-current" : ""}`} />
            </button>
            {item.url && (
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(item.url, "_blank", "noopener,noreferrer");
                }}
                className="p-1.5 rounded-full bg-white/10 text-white/70 hover:text-white transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        <h3 className="text-white font-semibold leading-tight">{item.title}</h3>
        <div className="flex items-center gap-2 flex-wrap mt-auto">
          <span className="bg-white/10 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1 hover:bg-white/20 transition-colors cursor-pointer">
            <span className="bg-primary text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
              {item.ticker.shortSymbol.replace("$", "")}
            </span>
            {item.ticker.symbol}
          </span>
          {item.risks.map((risk, index) => (
            <RiskBadge key={index} risk={risk} />
          ))}
        </div>
      </div>
    </div>
  )
}
