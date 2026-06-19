"use client"

import { motion } from "framer-motion"
import type React from "react"
import type { ComponentSize } from "../CanvasLayout"

export interface NewsItem {
  headline: string
  source: string
  timestamp: string
  sentimentScore: number
}

export interface NewsSentimentStreamProps {
  newsItems?: NewsItem[]
}

interface NewsSentimentStreamComponent
  extends React.FC<NewsSentimentStreamProps> {
  canvasSize?: ComponentSize
}

// Helper to get color values
const getSentimentColor = (score: number): string => {
  if (score > 0.3) return "#00b894" // positive
  if (score < -0.3) return "#d63031" // negative
  return "#6366f1" // neutral
}

export const NewsSentimentStream: NewsSentimentStreamComponent = ({
  newsItems = [],
}) => {
  const items = Array.isArray(newsItems) ? newsItems : []

  return (
    <div className="w-full h-full flex flex-col bg-[#0f2424] rounded-xl overflow-hidden shadow-xl border border-[#1f3030]">
      {/* Header: Reduced padding and font size */}
      <div className="px-4 py-3 border-b border-[#2d3748] bg-[#0f2424]/50 backdrop-blur-sm shrink-0">
        <h2 className="text-white text-sm font-semibold flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          News Stream
        </h2>
      </div>

      {/* Scrollable Content Area */}
      {items.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-[#6b7280] text-xs text-center">
            No active signals.
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-0 scrollbar-thin scrollbar-thumb-[#3f3f46] scrollbar-track-transparent">
          <div className="flex flex-col">
            {items.map((item, index) => {
              const color = getSentimentColor(item.sentimentScore)
              
              return (
                <motion.div
                  key={`${item.headline}-${index}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="group relative px-4 py-3 border-b border-[#1f3030] last:border-b-0 hover:bg-[#162e2e] transition-colors cursor-default"
                >
                  {/* Visual Sentiment Indicator (Left Border) */}
                  <div 
                    className="absolute left-0 top-0 bottom-0 w-1" 
                    style={{ backgroundColor: color, opacity: Math.abs(item.sentimentScore) }} 
                  />

                  <div className="pl-2">
                    {/* Header Row: Headline */}
                    <h3 className="text-gray-100 text-xs font-medium leading-snug line-clamp-2 mb-1.5 group-hover:text-white">
                      {item.headline}
                    </h3>

                    {/* Metadata Row: Compact Flex */}
                    <div className="flex items-center justify-between text-[10px] text-[#808d9e]">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-[#a0aec0]">{item.source}</span>
                        <span>•</span>
                        <span>{item.timestamp}</span>
                      </div>
                      
                      {/* Mini Sentiment Badge instead of Bar */}
                      <div 
                        className="px-1.5 py-0.5 rounded flex items-center gap-1 bg-opacity-10"
                        style={{ backgroundColor: `${color}20` }}
                      >
                         <div 
                           className="w-1.5 h-1.5 rounded-full" 
                           style={{ backgroundColor: color }}
                         />
                         <span style={{ color: color }}>
                           {item.sentimentScore > 0 ? '+' : ''}{item.sentimentScore.toFixed(1)}
                         </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// Changed to small to reflect the optimization
NewsSentimentStream.canvasSize = "medium"