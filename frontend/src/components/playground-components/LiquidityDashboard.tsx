"use client"

import React from "react"
import { Droplet } from "lucide-react"
import { motion } from "framer-motion"
import type { ComponentSize } from "../CanvasLayout"

interface MetricItem {
  title: string
  value: string | number | null | undefined
}

interface LiquidityDashboardProps {
  metrics: MetricItem[]
}

// Small helper to format values and apply fallback
function formatValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "Not Applicable"
  if (typeof value === "number") {
    if (Number.isNaN(value)) return "Not Applicable"
    return value.toLocaleString()
  }
  if (typeof value === "string" && value.trim() === "") return "Not Applicable"
  return String(value)
}

function MetricCard({ item, index }: { item: MetricItem; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="bg-[#0d2a2a] rounded-2xl border border-teal-700/40 p-6 min-w-[260px] shadow-lg"
    >
      <h3 className="text-gray-400 text-sm mb-3">{item.title}</h3>

      {/* Value with fallback applied */}
      <p className="text-4xl font-bold text-white">
        {formatValue(item.value)}
      </p>
    </motion.div>
  )
}

export const LiquidityDashboard: React.FC<LiquidityDashboardProps> & {
  canvasSize?: ComponentSize
} = ({ metrics }) => {
  return (
    <div className="space-y-6 w-full">
      {/* Hardcoded Title */}
      <div className="flex items-center gap-3">
        <Droplet className="w-8 h-8 text-teal-400" />
        <h2 className="text-2xl font-semibold text-white">
          Liquidity & Cash Flow Management
        </h2>
      </div>

      {/* Metric Cards */}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {metrics.slice(0, 3).map((metric, i) => (
          <MetricCard key={i} item={metric} index={i} />
        ))}
      </div>
    </div>
  )
}

LiquidityDashboard.canvasSize = "large"
