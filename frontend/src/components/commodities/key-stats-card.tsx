interface KeyStatsData {
  open: number
  high: number
  low: number
  volume: string
  marketCap: string
  weekHigh52: number
}

interface KeyStatsCardProps {
  data: KeyStatsData
}

export function KeyStatsCard({ data }: KeyStatsCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-sm text-white/70 mb-4">Key Stats</h3>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-white/70 mb-1">Open</p>
          <p className="text-sm font-semibold text-white">
            ${data.open.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        <div>
          <p className="text-xs text-white/70 mb-1">High</p>
          <p className="text-sm font-semibold text-white">
            ${data.high.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        <div>
          <p className="text-xs text-white/70 mb-1">Low</p>
          <p className="text-sm font-semibold text-white">
            ${data.low.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        <div>
          <p className="text-xs text-white/70 mb-1">Volume</p>
          <p className="text-sm font-semibold text-white">{data.volume}</p>
        </div>

        <div>
          <p className="text-xs text-white/70 mb-1">Market Cap</p>
          <p className="text-sm font-semibold text-white">{data.marketCap}</p>
        </div>

        <div>
          <p className="text-xs text-white/70 mb-1">52 Week High</p>
          <p className="text-sm font-semibold text-white">
            ${data.weekHigh52.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>
    </div>
  )
}
