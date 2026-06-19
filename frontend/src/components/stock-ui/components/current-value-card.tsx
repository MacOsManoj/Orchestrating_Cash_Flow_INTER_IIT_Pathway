import { ChevronRight } from "lucide-react"
import { type StockData, timePeriods, chartIndicators, chartData } from "../data/stock-data"

interface CurrentValueCardProps {
  data: StockData
}

export function CurrentValueCard({ data }: CurrentValueCardProps) {
  return (
    <div className="border border-teal-700/50 rounded-lg p-6 bg-[#0a2428]">
      <p className="text-sm text-gray-400 mb-2">Current Value:</p>
      <h2 className="text-4xl font-bold text-red-500 mb-4">Rs. {data.currentValue.toLocaleString("en-IN")}/-</h2>
      <div className="flex justify-between text-sm text-gray-400 mb-6">
        <span>Invested amount: Rs. {data.investedAmount.toLocaleString("en-IN")}/-</span>
        <span>
          High/Low: Rs. {data.highValue} / {data.lowValue}
        </span>
      </div>

      {/* Time period buttons */}
      <div className="flex gap-2 mb-4">
        {timePeriods.map((period) => (
          <button
            key={period.value}
            className={`px-3 py-1 rounded border text-sm ${
              period.value === "1m"
                ? "border-emerald-500 bg-emerald-500/20 text-emerald-500"
                : "border-gray-600 text-gray-400 hover:border-emerald-500"
            }`}
          >
            {period.label}
          </button>
        ))}
        <button className="px-3 py-1 rounded border border-emerald-500 bg-emerald-500/20 text-emerald-500 text-sm">
          Volume
        </button>
        {chartIndicators.slice(1).map((indicator) => (
          <button
            key={indicator.value}
            className="px-3 py-1 rounded border border-gray-600 text-gray-400 text-sm hover:border-emerald-500"
          >
            {indicator.label}
          </button>
        ))}
        <button className="ml-auto p-1 rounded border border-gray-600 text-gray-400 hover:border-emerald-500">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Chart placeholder */}
      <div className="relative h-64 bg-[#051719] rounded border border-teal-700/30 p-4">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 pr-2">
          <span>180</span>
          <span>175</span>
          <span>170</span>
          <span>165</span>
          <span>160</span>
        </div>

        {/* Simple candlestick visualization */}
        <div className="ml-8 h-full flex items-end gap-1">
          {chartData.map((candle, index) => {
            const isGreen = candle.close > candle.open
            const heightPercent = ((candle.high - 160) / (180 - 160)) * 100
            const volumePercent = (candle.volume / 80) * 30

            return (
              <div key={index} className="flex-1 flex flex-col justify-end items-center gap-1">
                {/* Candlestick */}
                <div className="w-full relative" style={{ height: `${heightPercent}%` }}>
                  <div
                    className={`w-full ${isGreen ? "bg-emerald-500" : "bg-red-500"} opacity-80`}
                    style={{
                      height: `${Math.abs(candle.close - candle.open) * 2}px`,
                      marginTop: `${(180 - Math.max(candle.open, candle.close)) * 2}px`,
                    }}
                  />
                </div>
                {/* Volume bar */}
                <div className="w-full bg-teal-500/50" style={{ height: `${volumePercent}px` }} />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
