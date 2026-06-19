"use client"

import { stockInfo } from "../data/options-data/stockData"

interface MetricItemProps {
  label: string
  value: string | number
}

function MetricItem({ label, value }: MetricItemProps) {
  return (
    <div className="space-y-1">
      <div className="text-sm text-teal-400/80">{label}</div>
      <div className="text-xl md:text-2xl font-bold text-white">{value}</div>
    </div>
  )
}

export function KeyMetrics() {
  return (
    <div className="bg-[#143432]/40 border border-teal-900/40 rounded-lg p-4 md:p-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-6">
        <MetricItem label="Spot Price" value={`$${stockInfo.spotPrice.toFixed(2)}`} />
        <MetricItem label="Implied volatility" value={`${stockInfo.impliedVolatility}%`} />
        <MetricItem label="Volume" value={stockInfo.volume} />
        <MetricItem label="Holdings %" value={`${stockInfo.holdingsPercent}%`} />
        <MetricItem label="Last updated" value={stockInfo.lastUpdated} />
      </div>
    </div>
  )
}
