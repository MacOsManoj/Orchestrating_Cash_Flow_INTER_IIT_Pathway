"use client"

import { motion } from "framer-motion"
import { TrendingDown, TrendingUp } from "lucide-react"
import type { ComponentSize } from "../CanvasLayout"

interface StockPriceHeaderProps {
  stockName?: string
  percentageChange?: string
  absoluteChange?: string
  timestamp?: string
  currency?: string
  exchange?: string
}

interface StockPriceHeaderComponent
  extends React.FC<StockPriceHeaderProps> {
  canvasSize?: ComponentSize
}

export const StockPriceHeader: StockPriceHeaderComponent = ({
  stockName = "",
  percentageChange = "",
  absoluteChange = "",
  timestamp = "",
  currency = "INR",
  exchange = "BSE",
}) => {
  // Convert to string and handle edge cases
  const percentageChangeStr = String(percentageChange || "")
  const absoluteChangeStr = String(absoluteChange || "")
  
  const isNegative = percentageChangeStr.includes("-")
  const Icon = isNegative ? TrendingDown : TrendingUp

  const hasMovementData =
    percentageChangeStr.trim() !== "" || absoluteChangeStr.trim() !== ""

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="w-full h-full"
    >
      <div className="w-full h-full rounded-2xl bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 border border-slate-800 px-3 py-3 sm:px-4 sm:py-3.5 md:px-4 md:py-4 flex flex-col gap-1.5 sm:gap-2 md:gap-2.5">
        {/* STOCK NAME */}
        {stockName && (
          <h2 className="text-white text-sm sm:text-base md:text-lg font-bold tracking-tight leading-tight">
            {stockName}
          </h2>
        )}

        {/* PRICE MOVEMENT */}
        {hasMovementData && (
          <div className="flex items-center gap-2 sm:gap-3 md:gap-3.5">
            <Icon
              className={`w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7 flex-shrink-0 ${
                isNegative ? "text-red-500" : "text-emerald-500"
              }`}
            />

            <div className="flex flex-col gap-0.5 sm:gap-1">
              {percentageChangeStr && (
                <span
                  className={`text-xl sm:text-2xl md:text-3xl font-bold leading-tight ${
                    isNegative ? "text-red-500" : "text-emerald-500"
                  }`}
                >
                  {percentageChangeStr}
                </span>
              )}

              {absoluteChangeStr && (
                <span
                  className={`text-xs sm:text-sm md:text-base font-semibold leading-tight ${
                    isNegative ? "text-red-500" : "text-emerald-500"
                  }`}
                >
                  {absoluteChangeStr} Today
                </span>
              )}
            </div>
          </div>
        )}

        {/* TIMESTAMP + MARKET CONTEXT */}
        {(timestamp || currency || exchange) && (
          <div className="text-slate-400 text-[10px] sm:text-[11px] md:text-xs leading-tight mt-0.5">
            {timestamp && <span>{timestamp}</span>}
            {(currency || exchange) && (
              <>
                {" · "}
                {currency}
                {" · "}
                {exchange}
              </>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}

// Size for your packing algorithm
StockPriceHeader.canvasSize = "small"
