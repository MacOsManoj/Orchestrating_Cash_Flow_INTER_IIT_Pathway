export function AssetDistributionChart() {
  const data = [
    { label: "Stocks and derivatives", percentage: 40, color: "text-accent-magenta", dotColor: "bg-accent-magenta" },
    { label: "Bonds", percentage: 25, color: "text-accent-magenta", dotColor: "bg-accent-magenta" },
    { label: "FX", percentage: 10, color: "text-accent-green", dotColor: "bg-accent-green" },
    { label: "Commodities", percentage: 25, color: "text-accent-blue", dotColor: "bg-accent-blue" },
  ]

  return (
    <div className="flex flex-col md:flex-row items-center gap-6">
      {/* Chart */}
      <div className="relative flex-shrink-0">
        <svg width="180" height="180" viewBox="0 0 180 180" className="transform -rotate-90">
          {/* Background circle */}
          <circle cx="90" cy="90" r="70" fill="none" stroke="hsl(var(--color-border))" strokeWidth="28" />
          {/* Segments */}
          <circle
            cx="90"
            cy="90"
            r="70"
            fill="none"
            stroke="hsl(var(--color-accent-magenta))"
            strokeWidth="28"
            strokeDasharray="175.93 439.82"
            strokeDashoffset="0"
            className="transition-all duration-500"
          />
          <circle
            cx="90"
            cy="90"
            r="70"
            fill="none"
            stroke="hsl(var(--color-accent-magenta))"
            strokeWidth="28"
            strokeDasharray="109.96 439.82"
            strokeDashoffset="-175.93"
            className="transition-all duration-500"
          />
          <circle
            cx="90"
            cy="90"
            r="70"
            fill="none"
            stroke="hsl(var(--color-accent-green))"
            strokeWidth="28"
            strokeDasharray="43.98 439.82"
            strokeDashoffset="-285.89"
            className="transition-all duration-500"
          />
          <circle
            cx="90"
            cy="90"
            r="70"
            fill="none"
            stroke="hsl(var(--color-accent-blue))"
            strokeWidth="28"
            strokeDasharray="109.96 439.82"
            strokeDashoffset="-329.87"
            className="transition-all duration-500"
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-xs text-text-muted">Total Value</p>
          <p className="text-xl font-bold text-text-primary">$ 1.23 M</p>
        </div>
      </div>

      {/* Legend */}
      <div className="flex-1 space-y-3">
        <h3 className="text-base font-semibold text-text-primary mb-4">Asset distribution</h3>
        {data.map((item, index) => (
          <div key={index} className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${item.dotColor}`} />
            <div className="flex-1">
              <p className="text-sm text-text-primary">{item.label}</p>
              <p className="text-xs text-text-muted">{item.percentage}%</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
