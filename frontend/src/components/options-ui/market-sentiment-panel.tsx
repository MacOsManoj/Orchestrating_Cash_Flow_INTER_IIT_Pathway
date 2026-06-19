"use client"

import { marketSentiment } from "../data/options-data/stockData"

interface SentimentItemProps {
  label: string
  value: string
  highlight?: boolean
}

function SentimentItem({ label, value, highlight }: SentimentItemProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-teal-400/80">{label}</span>
      <span className={`text-base font-semibold ${highlight ? "text-teal-300" : "text-white"}`}>{value}</span>
    </div>
  )
}

export function MarketSentimentPanel() {
  return (
    <div className="bg-[#143432]/40 border border-teal-900/40 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4 text-center">Market sentiment</h3>

      <div className="space-y-1 divide-y divide-teal-900/20">
        <SentimentItem label="Put/ Call ratio" value={marketSentiment.putCallRatio.toString()} />
        <SentimentItem label="Volume spike" value={marketSentiment.volumeSpike} highlight />
        <SentimentItem label="IV rank" value={marketSentiment.ivRank} />
      </div>
    </div>
  )
}
