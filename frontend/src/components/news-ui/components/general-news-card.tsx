"use client"

import type React from "react"

import { useState } from "react"
import type { GeneralNewsItem } from "../data/news"
import { XCircle, CheckCircle, MinusCircle, Share2, Bookmark, ChevronDown, ChevronUp } from "lucide-react"

interface GeneralNewsCardProps {
  item: GeneralNewsItem
  onBookmark?: (id: string) => void
  onClick?: (item: GeneralNewsItem) => void
}

export function GeneralNewsCard({ item, onBookmark, onClick }: GeneralNewsCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsBookmarked(!isBookmarked)
    onBookmark?.(item.id)
  }

  const handleShare = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(item.title)
  }

  const toggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsExpanded(!isExpanded)
  }

  const getSentimentIcon = () => {
    switch (item.sentiment) {
      case "Bullish":
        return <CheckCircle className="w-4 h-4 text-emerald-400" />
      case "Bearish":
        return <XCircle className="w-4 h-4 text-red-400" />
      default:
        return <MinusCircle className="w-4 h-4 text-gray-400" />
    }
  }

  const getSentimentColor = () => {
    switch (item.sentiment) {
      case "Bullish":
        return "text-emerald-400"
      case "Bearish":
        return "text-red-400"
      default:
        return "text-gray-400"
    }
  }

  return (
    <div
      className={`bg-card rounded-xl p-4 border border-border cursor-pointer
        transition-all duration-300 ease-out
        ${isHovered ? "bg-card border-primary/50 shadow-lg shadow-primary/10 -translate-y-1" : ""}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onClick?.(item)}
    >
      <div className="flex gap-4">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <div className="text-white/70 text-sm">
              {item.source} - {item.timeAgo}
            </div>
            <div className={`flex gap-2 transition-opacity duration-200 ${isHovered ? "opacity-100" : "opacity-0"}`}>
              <button
                onClick={handleShare}
                className="p-1.5 rounded-full bg-white/10 text-white/70 hover:text-white transition-colors"
              >
                <Share2 className="w-4 h-4" />
              </button>
              <button
                onClick={handleBookmark}
                className={`p-1.5 rounded-full transition-colors ${
                  isBookmarked ? "bg-primary text-white" : "bg-white/10 text-white/70 hover:text-white"
                }`}
              >
                <Bookmark className={`w-4 h-4 ${isBookmarked ? "fill-current" : ""}`} />
              </button>
            </div>
          </div>
          <h3 className="text-white font-semibold text-lg mb-2">{item.title}</h3>
          <p className={`text-white/70 text-sm mb-3 transition-all duration-300 ${isExpanded ? "" : "line-clamp-2"}`}>
            {item.description}
          </p>
          <div className="flex items-center justify-between">
            <div className={`flex items-center gap-1 ${getSentimentColor()}`}>
              {getSentimentIcon()}
              <span className="text-sm">{item.sentiment}</span>
            </div>
            <button
              onClick={toggleExpand}
              className="text-slate-400 hover:text-white text-sm flex items-center gap-1 transition-colors"
            >
              {isExpanded ? (
                <>
                  Show less <ChevronUp className="w-4 h-4" />
                </>
              ) : (
                <>
                  Read more <ChevronDown className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
        <div className="w-36 h-28 rounded-lg overflow-hidden flex-shrink-0">
          <img
            src={item.imageUrl || "/placeholder.svg"}
            alt={item.title}
            className={`w-full h-full object-cover transition-transform duration-500 ${isHovered ? "scale-110" : ""}`}
          />
        </div>
      </div>
    </div>
  )
}
