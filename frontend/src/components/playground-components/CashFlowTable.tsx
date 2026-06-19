"use client"

import { ArrowUp, ArrowDown } from "lucide-react"
import { motion } from "framer-motion"
import type { ComponentSize } from "../CanvasLayout"

export interface CashFlowRow {
  date?: string
  openingBalance?: string
  inflows: number
  outflows: number
  netCashFlow: number
  endingBalance?: string
  lcrPercentage: number
}

interface CashFlowTableProps {
  rows: CashFlowRow[]
}

interface CashFlowTableComponent extends React.FC<CashFlowTableProps> {
  canvasSize?: ComponentSize
}

const formatCurrency = (value: number): string => {
  return `$${Math.abs(value).toLocaleString("en-US")}`
}

export const CashFlowTable: CashFlowTableComponent = ({ rows }) => {
  const safeRows = Array.isArray(rows) ? rows : []

  const hasAnyData = safeRows.length > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="
        w-full h-full
        rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950
        border border-slate-800 p-6
        overflow-x-auto
      "
    >
      {/* Title */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-white text-xl font-bold">
          Cash flow & LCR by period
        </h3>
      </div>

      {!hasAnyData ? (
        <p className="text-slate-500 text-sm">No cash flow data available.</p>
      ) : (
        <div className="min-w-[900px] rounded-2xl overflow-hidden border border-slate-800">
          {/* Header */}
          <div className="grid grid-cols-7 bg-slate-800/80 text-slate-200 text-xs font-semibold uppercase tracking-wide">
            <div className="px-4 py-3 border-r border-slate-700">Date</div>
            <div className="px-4 py-3 border-r border-slate-700">
              Opening balance
            </div>
            <div className="px-4 py-3 border-r border-slate-700">Inflows</div>
            <div className="px-4 py-3 border-r border-slate-700">
              Outflows
            </div>
            <div className="px-4 py-3 border-r border-slate-700">
              Net cash flow
            </div>
            <div className="px-4 py-3 border-r border-slate-700">
              Ending balance
            </div>
            <div className="px-4 py-3">LCR %</div>
          </div>

          {/* Rows */}
          {safeRows.map((row, index) => {
            const hasInflows = typeof row.inflows === "number"
            const hasOutflows = typeof row.outflows === "number"
            const hasNet = typeof row.netCashFlow === "number"
            const hasLcr = typeof row.lcrPercentage === "number"

            return (
              <div
                key={index}
                className="grid grid-cols-7 items-center text-sm text-slate-100 border-t border-slate-800/70"
              >
                {/* Date */}
                <div className="px-4 py-3 text-left text-slate-300">
                  {row.date || "-"}
                </div>

                {/* Opening Balance */}
                <div className="px-4 py-3 text-left text-slate-300">
                  {row.openingBalance || "-"}
                </div>

                {/* Inflows */}
                <div className="px-4 py-3 flex items-center justify-center gap-2">
                  {hasInflows ? (
                    <>
                      <ArrowUp className="text-emerald-400 w-4 h-4" />
                      <span className="font-semibold text-emerald-400">
                        {formatCurrency(row.inflows)}
                      </span>
                    </>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </div>

                {/* Outflows */}
                <div className="px-4 py-3 flex items-center justify-center gap-2">
                  {hasOutflows ? (
                    <>
                      <ArrowDown className="text-red-400 w-4 h-4" />
                      <span className="font-semibold text-red-400">
                        {formatCurrency(row.outflows)}
                      </span>
                    </>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </div>

                {/* Net Cash Flow */}
                <div className="px-4 py-3 text-center">
                  {hasNet ? (
                    <span
                      className={`font-semibold ${
                        row.netCashFlow >= 0
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {row.netCashFlow >= 0 ? "+" : "-"}
                      {formatCurrency(row.netCashFlow)}
                    </span>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </div>

                {/* Ending Balance */}
                <div className="px-4 py-3 text-left text-slate-300">
                  {row.endingBalance || "-"}
                </div>

                {/* LCR % */}
                <div className="px-4 py-3 flex justify-center">
                  {hasLcr ? (
                    <span className="px-4 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-semibold">
                      {row.lcrPercentage}%
                    </span>
                  ) : (
                    <span className="text-slate-500 text-xs">-</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </motion.div>
  )
}

// This is a wide table → treat as full-width in your packing logic
CashFlowTable.canvasSize = "full"
