"use client"

import { useState } from "react"
import type { RiskBadge as RiskBadgeType } from "../data/news"

interface RiskBadgeProps {
  risk: RiskBadgeType
  onClick?: (risk: RiskBadgeType) => void
}

export function RiskBadge({ risk, onClick }: RiskBadgeProps) {
  const [isHovered, setIsHovered] = useState(false)

  const getLevelColor = (level: string) => {
    switch (level) {
      case "Low":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/30"
      case "Medium":
        return "bg-amber-500/20 text-amber-400 border-amber-500/30 hover:bg-amber-500/30"
      case "High":
        return "bg-red-500/20 text-red-400 border-red-500/30 hover:bg-red-500/30"
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/30 hover:bg-gray-500/30"
    }
  }

  const getRiskDescription = () => {
    const descriptions: Record<string, Record<string, string>> = {
      "Market Risk": {
        Low: "Minimal market volatility expected",
        Medium: "Moderate market fluctuations possible",
        High: "Significant market swings likely",
      },
      "Volatility Risk": {
        Low: "Price stability expected",
        Medium: "Some price volatility anticipated",
        High: "High price swings expected",
      },
      "Operational Risk": {
        Low: "Operations running smoothly",
        Medium: "Minor operational concerns",
        High: "Significant operational issues",
      },
      "Regulatory Risk": {
        Low: "Favorable regulatory environment",
        Medium: "Regulatory changes possible",
        High: "Major regulatory challenges ahead",
      },
    }
    return descriptions[risk.type]?.[risk.level] || "Risk assessment"
  }

  return (
    <div className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation()
          onClick?.(risk)
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={`px-2 py-0.5 text-xs rounded-full border cursor-pointer transition-all duration-200
          ${getLevelColor(risk.level)} ${isHovered ? "scale-105" : ""}`}
      >
        {risk.type}: {risk.level}
      </button>
      {isHovered && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-background border border-border rounded-lg text-xs text-white whitespace-nowrap z-10 shadow-xl animate-in fade-in-0 zoom-in-95 duration-200">
          {getRiskDescription()}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-background" />
        </div>
      )}
    </div>
  )
}
