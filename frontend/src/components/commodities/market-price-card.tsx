import { TrendingUp } from "lucide-react"

interface MarketPriceData {
  currentPrice: number
  change24h: {
    value: number
    percentage: number
    isPositive: boolean
  }
}

interface MarketPriceCardProps {
  data: MarketPriceData
}

export function MarketPriceCard({ data }: MarketPriceCardProps) {
  const { currentPrice, change24h } = data
  const changeColor = change24h.isPositive ? "#22c55e" : "#ef4444"
  const changePrefix = change24h.isPositive ? "+" : ""

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="space-y-4">
        <h3 className="text-sm text-white/70">Current Market Price</h3>
        <p className="text-4xl font-bold text-white">
          ${currentPrice.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>

        <div className="pt-4 border-t border-border">
          <p className="text-sm text-white/70 mb-2">24-hour Change</p>
          <div className="flex items-center gap-2">
            <span style={{ color: changeColor }} className="text-lg font-semibold">
              {changePrefix}${change24h.value.toFixed(2)}
            </span>
            <span style={{ color: changeColor }} className="text-sm flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              {changePrefix}
              {change24h.percentage.toFixed(2)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
