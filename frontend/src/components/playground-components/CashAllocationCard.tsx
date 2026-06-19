// src/components/playground-components/CashAllocationCard.tsx
"use client"

import React from "react"
import { Building2, TrendingUp } from "lucide-react"
import { motion } from "framer-motion"
import type { ComponentSize } from "../CanvasLayout"

interface CashAllocationCardProps {
  title?: string
  subtitle?: string
  freeCashLabel?: string
  investedLabel?: string
  freeCashAmount?: number
  investedAmount?: number
}

interface CashAllocationCardComponent
  extends React.FC<CashAllocationCardProps> {
  canvasSize?: ComponentSize
}

export const CashAllocationCard: CashAllocationCardComponent = ({
  title = "Cash & Investments",
  subtitle = "Across all asset classes",
  freeCashLabel = "Free Cash Available",
  investedLabel = "Amount Invested",
  freeCashAmount,
  investedAmount
}) => {
  const currencySymbol = "₹"  // 🔥 Hard-coded as requested

  const formatAmount = (value: number | undefined) => {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return `${currencySymbol}—`
    }

    const abs = Math.abs(value)
    if (abs >= 1_000_000) {
      return `${value < 0 ? "-" : ""}${currencySymbol}${(abs / 1_000_000).toFixed(1)}M`
    }
    return `${value < 0 ? "-" : ""}${currencySymbol}${abs.toLocaleString()}`
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25 }}
      className="w-full h-full bg-[#0d2d2f] rounded-lg border border-teal-700/60 p-3 sm:p-4 shadow-lg"
    >
      <div className="flex flex-col gap-4 h-full">
        {/* Header */}
        <div>
          <h2 className="text-sm sm:text-base font-semibold text-white leading-tight">
            {title}
          </h2>
          {subtitle && (
            <p className="text-[11px] sm:text-xs text-gray-400 mt-0.5 leading-tight">
              {subtitle}
            </p>
          )}
        </div>

        {/* Free Cash */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Building2 className="w-4 h-4 text-gray-400" />
            <h3 className="text-[11px] sm:text-xs md:text-sm text-gray-300">
              {freeCashLabel}
            </h3>
          </div>
          <p className="text-2xl sm:text-3xl md:text-4xl font-bold text-emerald-400 leading-tight">
            {formatAmount(freeCashAmount)}
          </p>
        </div>

        {/* Invested */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <TrendingUp className="w-4 h-4 text-gray-400" />
            <h3 className="text-[11px] sm:text-xs md:text-sm text-gray-300">
              {investedLabel}
            </h3>
          </div>
          <p className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-100 leading-tight">
            {formatAmount(investedAmount)}
          </p>
        </div>
      </div>
    </motion.div>
  )
}

CashAllocationCard.canvasSize = "small"
