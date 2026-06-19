interface HoldingsData {
  totalValue: number
  percentOfCommodity: number
  avgBuyPrice: number
  unrealizedGainLoss: {
    value: number
    isPositive: boolean
  }
  portfolioExposure: number
}

interface HoldingsCardProps {
  data: HoldingsData
}

export function HoldingsCard({ data }: HoldingsCardProps) {
  const glColor = data.unrealizedGainLoss.isPositive ? "#22c55e" : "#ef4444"
  const glPrefix = data.unrealizedGainLoss.isPositive ? "+" : ""

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm text-white/70 mb-2">Your Holdings</h3>
            <p className="text-4xl font-bold text-white">
              ${data.totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-white/70">% of</p>
            <p className="text-xs text-white/70">Commodity</p>
            <p className="text-2xl font-bold text-white mt-1">{data.percentOfCommodity}%</p>
          </div>
        </div>

        <div className="pt-4 border-t border-border grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-white/70 mb-1">Avg. Buy Price</p>
            <p className="text-sm font-semibold text-white">
              ${data.avgBuyPrice.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>

          <div>
            <p className="text-xs text-white/70 mb-1">Unrealized G/L</p>
            <p style={{ color: glColor }} className="text-sm font-semibold">
              {glPrefix}$
              {data.unrealizedGainLoss.value.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </div>

          <div>
            <p className="text-xs text-white/70 mb-1">Portfolio</p>
            <p className="text-xs text-white/70">Exposure</p>
            <p className="text-sm font-semibold text-white">{data.portfolioExposure}%</p>
          </div>
        </div>
      </div>
    </div>
  )
}
