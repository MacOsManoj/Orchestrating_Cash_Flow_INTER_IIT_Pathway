export function KeyMetrics() {
  const metrics = [
    { label: "Volatility", value: "15.2%" },
    { label: "VaR (95%)", value: "-$25,310" },
    { label: "Beta", value: "1.15" },
    { label: "Expected Shortfall", value: "-$42,780" },
  ]

  const holdings = [
    { name: "Microsoft Corp", percentage: 85 },
    { name: "Microsoft Corp", percentage: 75 },
    { name: "Microsoft Corp", percentage: 70 },
    { name: "Microsoft Corp", percentage: 60 },
  ]

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-base font-semibold text-white mb-6">Key metrics</h3>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        {metrics.map((metric, index) => (
          <div key={index}>
            <p className="text-xs text-text-muted mb-1">{metric.label}</p>
            <p className="text-lg font-bold text-white">{metric.value}</p>
          </div>
        ))}
      </div>

      {/* Holdings */}
      <div className="flex-1">
        <h4 className="text-sm font-semibold text-white mb-4">Top 5 Holdings / Counterparty Exposure %</h4>
        <div className="space-y-3">
          {holdings.map((holding, index) => (
            <div key={index} className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-bold text-background">MS</span>
              </div>
              <div className="flex-1">
                <p className="text-sm text-white mb-1">{holding.name}</p>
                <div className="h-2 bg-border rounded-full overflow-hidden">
                  <div className="h-full bg-accent-blue rounded-full" style={{ width: `${holding.percentage}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
