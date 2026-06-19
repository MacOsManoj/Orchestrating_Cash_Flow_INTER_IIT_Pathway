"use client"

import { optionChainData, type OptionChainRow } from "../data/options-data/stockData"
import { cn } from "@/lib/utils"

export function OptionsChainTable() {
  return (
    <div className="bg-[#143432]/40 border border-teal-900/40 rounded-lg overflow-hidden">
      {/* Table Header */}
      <div className="grid grid-cols-6 gap-4 p-4 bg-[#0f1f1e] border-b border-teal-900/40 text-sm text-teal-400/80 font-medium">
        <div>STRIKE</div>
        <div>ASK</div>
        <div>VOLUME</div>
        <div>OPEN INT.</div>
        <div>IV</div>
        <div>DELTA</div>
      </div>

      {/* Table Body */}
      <div className="divide-y divide-teal-900/20">
        {optionChainData.map((row, index) => (
          <OptionsChainRow key={index} data={row} />
        ))}
      </div>
    </div>
  )
}

interface OptionsChainRowProps {
  data: OptionChainRow
}

function OptionsChainRow({ data }: OptionsChainRowProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-6 gap-4 p-4 text-sm transition-colors",
        data.isHighlighted ? "bg-amber-900/20 border-l-2 border-amber-500" : "hover:bg-teal-950/20",
      )}
    >
      <div className="font-medium text-white">{data.strike}</div>
      <div className={cn("font-medium", data.isHighlighted ? "text-amber-400" : "text-teal-300")}>
        {data.ask.toFixed(2)}
      </div>
      <div className={cn(data.isHighlighted ? "text-amber-400" : "text-teal-300")}>{data.volume}</div>
      <div className={cn(data.isHighlighted ? "text-amber-400" : "text-teal-300")}>{data.openInterest}</div>
      <div className={cn(data.isHighlighted ? "text-amber-400" : "text-teal-300")}>{data.iv}</div>
      <div className={cn(data.isHighlighted ? "text-amber-400" : "text-teal-300")}>{data.delta.toFixed(2)}</div>
    </div>
  )
}
