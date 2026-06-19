"use client"

import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import { payoffPosition } from "../data/options-data/stockData"

interface MetricRowProps {
  label: string
  value: string | number
  valueColor?: string
}

function MetricRow({ label, value, valueColor = "text-white" }: MetricRowProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-teal-400/80">{label}</span>
      <span className={`text-base font-semibold ${valueColor}`}>{value}</span>
    </div>
  )
}

export function PayoffSimulator() {
  return (
    <div className="bg-[#143432]/40 border border-teal-900/40 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Payoff Simulator</h3>

      <div className="space-y-4">
        {/* Position Type */}
        <div className="text-sm text-teal-400/80 mb-2">Position 1: {payoffPosition.type}</div>

        {/* Strike and Premium */}
        <div className="grid grid-cols-2 gap-4">
          <MetricRow label="Strike" value={payoffPosition.strike.toFixed(2)} />
          <MetricRow label="Premium" value={payoffPosition.premium.toFixed(2)} />
        </div>

        {/* Add Leg Button */}
        <Button
          variant="outline"
          className="w-full border-dashed border-teal-600/50 text-teal-400 hover:bg-teal-950/30 hover:text-teal-300 py-8 bg-transparent"
        >
          <Plus className="mr-2 h-5 w-5" />
          Add Leg
        </Button>

        {/* Profit/Loss Metrics */}
        <div className="pt-4 border-t border-teal-900/30 space-y-2">
          <MetricRow label="Max Profit" value={payoffPosition.maxProfit} valueColor="text-teal-400" />
          <MetricRow label="Max Loss" value={payoffPosition.maxLoss} valueColor="text-red-400" />
          <MetricRow label="Break-even" value={`$${payoffPosition.breakEven.toFixed(2)}`} />
        </div>
      </div>
    </div>
  )
}
