"use client"

import type React from "react"

import { useState, useEffect } from "react"
import type { TrendingTopic } from "../data/news"
import { TrendingUp, TrendingDown, Plus, Check } from "lucide-react"

// Watchlist storage key
const WATCHLIST_KEY = "news_watchlist_companies"

// Helper to get watchlist from localStorage
export function getWatchlistCompanies(): string[] {
  try {
    const stored = localStorage.getItem(WATCHLIST_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

// Helper to save watchlist to localStorage
export function saveWatchlistCompanies(companies: string[]): void {
  try {
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(companies))
  } catch (error) {
    console.error("Failed to save watchlist:", error)
  }
}

interface TrendingTopicsProps {
  topics: TrendingTopic[]
  onTopicClick?: (topic: TrendingTopic) => void
  onAddToWatchlist?: (company: string) => void
}

export function TrendingTopics({ topics, onTopicClick, onAddToWatchlist }: TrendingTopicsProps) {
  const [watchlist, setWatchlist] = useState<Set<string>>(new Set())
  const [hoveredTopic, setHoveredTopic] = useState<string | null>(null)

  // Load watchlist from localStorage on mount
  useEffect(() => {
    const companies = getWatchlistCompanies()
    setWatchlist(new Set(companies))
  }, [])

  const handleAddToWatchlist = (e: React.MouseEvent, topic: TrendingTopic) => {
    e.stopPropagation()
    const company = topic.label
    const newWatchlist = new Set(watchlist)
    
    if (newWatchlist.has(company)) {
      newWatchlist.delete(company)
    } else {
      newWatchlist.add(company)
    }
    
    setWatchlist(newWatchlist)
    saveWatchlistCompanies(Array.from(newWatchlist))
    onAddToWatchlist?.(company)
  }

  const isInWatchlist = (topic: TrendingTopic) => watchlist.has(topic.label)

  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <h3 className="text-white font-semibold text-lg mb-4">Trending Topics</h3>
      <div className="space-y-2">
        {topics.map((topic) => (
          <div
            key={topic.id}
            className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all duration-200
              ${hoveredTopic === topic.id ? "bg-white/5" : ""}`}
            onMouseEnter={() => setHoveredTopic(topic.id)}
            onMouseLeave={() => setHoveredTopic(null)}
            onClick={() => onTopicClick?.(topic)}
          >
            {/* Company/Sector Icon */}
            {topic.icon && (
              <span className="text-lg" role="img" aria-label={topic.label}>
                {topic.icon}
              </span>
            )}
            <div className={`transition-transform duration-200 ${hoveredTopic === topic.id ? "scale-125" : ""}`}>
              {topic.trend === "up" ? (
                <TrendingUp className="w-5 h-5 text-primary" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-400" />
              )}
            </div>
            <span className="text-white flex-1">{topic.label}</span>
            {/* Mention count badge */}
            {topic.count !== undefined && (
              <span className="text-xs text-white/70 bg-white/10 px-2 py-0.5 rounded-full">
                {topic.count} mentions
              </span>
            )}
            {/* Add to Watchlist Button */}
            <button
              onClick={(e) => handleAddToWatchlist(e, topic)}
              title={isInWatchlist(topic) ? "Remove from watchlist" : "Add to watchlist"}
              className={`p-1.5 rounded-full transition-all duration-200 ${
                isInWatchlist(topic)
                  ? "bg-primary text-white"
                  : hoveredTopic === topic.id
                    ? "bg-white/10 text-white/70 hover:bg-primary/20 hover:text-primary"
                    : "opacity-0"
              }`}
            >
              {isInWatchlist(topic) ? (
                <Check className="w-4 h-4" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
