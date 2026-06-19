"use client"

import { greeksData } from "../data/options-data/stockData"

interface GreekItemProps {
  label: string
  value: number
}

function GreekItem({ label, value }: GreekItemProps) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-teal-400/80">{label}</span>
      <span className="text-lg font-semibold text-white">{value.toFixed(2)}</span>
    </div>
  )
}

export function GreeksOverview() {
  return (
    <div className="bg-[#143432]/40 border border-teal-900/40 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-6 text-center">Greeks Overview</h3>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-6">
          <GreekItem label="Delta" value={greeksData.delta} />
          <GreekItem label="Gamma" value={greeksData.gamma} />
        </div>

        <div className="grid grid-cols-2 gap-6 pt-4 border-t border-teal-900/30">
          <GreekItem label="Theta" value={greeksData.theta} />
          <GreekItem label="Vega" value={greeksData.vega} />
        </div>
      </div>
    </div>
  )
}
