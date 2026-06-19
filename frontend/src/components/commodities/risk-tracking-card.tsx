import { AlertTriangle, XCircle } from "lucide-react"

interface Warning {
  type: string
  message: string
}

interface RiskTrackingData {
  historicalVolatility: number
  valueAtRisk: number
  beta: number
  liquidityScore: number
  warnings: Warning[]
}

interface RiskTrackingCardProps {
  data: RiskTrackingData
}

export function RiskTrackingCard({ data }: RiskTrackingCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Risk Tracking</h3>

      <div className="space-y-3">
        {/* Historical Volatility */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/70">Historical volatility</span>
          <span className="text-sm font-semibold text-white">{data.historicalVolatility}%</span>
        </div>

        {/* Value at Risk */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/70">Value at Risk (VaR 95%)</span>
          <span className="text-sm font-semibold text-white">${data.valueAtRisk.toLocaleString()}</span>
        </div>

        {/* Beta */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/70">Beta (vs. S&P 500)</span>
          <span className="text-sm font-semibold text-white">{data.beta.toFixed(2)}</span>
        </div>

        {/* Liquidity Score */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/70">Liquidity Score</span>
          <span className="text-sm font-semibold text-white">{data.liquidityScore}/100</span>
        </div>

        {/* Correlation Matrix */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-white/70">Correlation matrix</span>
          <button className="text-sm font-semibold text-primary hover:text-primary/80">View Matrix</button>
        </div>

        {/* Warnings */}
        <div className="pt-4 space-y-2">
          {data.warnings.map((warning, index) => (
            <div key={index} className="flex items-start gap-2">
              {warning.type === "high-volatility" ? (
                <AlertTriangle className="h-4 w-4 text-[#eab308] mt-0.5 flex-shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 text-[#ef4444] mt-0.5 flex-shrink-0" />
              )}
              <span className="text-xs text-white/70">{warning.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
