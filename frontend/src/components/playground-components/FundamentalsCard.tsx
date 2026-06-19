"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import type { ComponentSize } from "../CanvasLayout"

interface MetricItem {
  label: string
  value?: string | number | null
}

interface FundamentalsCardProps {
  companyName?: string
  fundamentals?: MetricItem[]
  technical?: MetricItem[]
}

interface FundamentalsCardComponent
  extends React.FC<FundamentalsCardProps> {
  canvasSize?: ComponentSize
}

const hasValue = (value: MetricItem["value"]): boolean => {
  if (value === null || value === undefined) return false
  if (typeof value === "string" && value.trim() === "") return false
  return true
}

const formatValue = (value: MetricItem["value"]): string => {
  if (value === null || value === undefined) return "-"
  if (typeof value === "number") {
    return value.toLocaleString(undefined, {
      maximumFractionDigits: 2,
    })
  }
  return String(value)
}

export const FundamentalsCard: FundamentalsCardComponent = ({
  companyName = "Company name",
  fundamentals = [],
  technical = [],
}) => {
  const [activeTab, setActiveTab] = useState<"technical" | "fundamentals">(
    "technical",
  )

  const cleanedFundamentals = fundamentals.filter((item) => hasValue(item.value))
  const cleanedTechnical = technical.filter((item) => hasValue(item.value))

  const itemsToRender =
    activeTab === "technical" ? cleanedTechnical : cleanedFundamentals

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 overflow-hidden w-full h-full"
    >
      {/* Tabs - compact */}
      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab("technical")}
          className={`flex-1 px-4 py-2.5 text-xs sm:text-sm font-semibold transition-colors relative ${
            activeTab === "technical" ? "text-white" : "text-slate-500"
          }`}
        >
          Technical
          {activeTab === "technical" && (
            <motion.div
              layoutId="fundamentalsCardActiveTab"
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500"
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          )}
        </button>

        <button
          onClick={() => setActiveTab("fundamentals")}
          className={`flex-1 px-4 py-2.5 text-xs sm:text-sm font-semibold transition-colors relative ${
            activeTab === "fundamentals" ? "text-white" : "text-slate-500"
          }`}
        >
          Fundamentals
          {activeTab === "fundamentals" && (
            <motion.div
              layoutId="fundamentalsCardActiveTab"
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500"
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          )}
        </button>
      </div>

      {/* Content - compact padding */}
      <div className="p-4 sm:p-5">
        <h3 className="text-white text-sm sm:text-base md:text-lg font-bold mb-4">
          {companyName}
        </h3>

        {itemsToRender.length === 0 ? (
          <p className="text-[11px] sm:text-sm text-slate-400">
            No {activeTab === "technical" ? "technical" : "fundamental"} data
            available.
          </p>
        ) : (
          <ul className="space-y-2.5 sm:space-y-3">
            {itemsToRender.map((item, index) => (
              <li
                key={`${item.label}-${index}`}
                className="flex items-center gap-2 text-xs sm:text-sm md:text-base text-white"
              >
                <span className="text-cyan-400 text-[10px] sm:text-xs">•</span>
                <span className="text-slate-200 truncate">{item.label}</span>
                <span className="ml-auto text-slate-100 whitespace-nowrap">
                  {formatValue(item.value)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </motion.div>
  )
}

// Default for your layout engine
FundamentalsCard.canvasSize = "medium"
