"use client"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown } from "lucide-react"
import { DashboardCard } from "./dashboard-card"

interface CashData {
  freeCash: number
  amountInvested: number
  change24h: number
  change24hPercent: number
}

const CASH_DATA: CashData = {
  freeCash: 12000,
  amountInvested: 12300000.43,
  change24h: 153750,
  change24hPercent: 1.25,
}

export function FreeCashCard() {
  const isPositive = CASH_DATA.change24hPercent >= 0

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
      <DashboardCard>
        <div className="flex flex-col h-full">
          <p className="text-sm text-white/70 mb-2">Free cash available</p>
          <p className="text-3xl font-bold text-white mb-4">${CASH_DATA.freeCash.toLocaleString()}</p>
          <p className="text-sm text-white/70 mb-1">Amount invested</p>
          <p className="text-2xl font-bold text-white mb-2">
            $
            {CASH_DATA.amountInvested.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <div className="flex items-center gap-2 text-sm mt-auto">
            {isPositive ? (
              <TrendingUp className="w-4 h-4 text-[#14B8A6]" />
            ) : (
              <TrendingDown className="w-4 h-4 text-[#EF4444]" />
            )}
            <span className={`font-semibold ${isPositive ? "text-[#14B8A6]" : "text-[#EF4444]"}`}>
              {isPositive ? "+" : ""}
              {CASH_DATA.change24hPercent}%
            </span>
            <span className="text-white/70">last 24h</span>
          </div>
        </div>
      </DashboardCard>
    </motion.div>
  )
}
