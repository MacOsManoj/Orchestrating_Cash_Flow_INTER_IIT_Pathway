import { AlertCircle, TrendingUp, Scale } from "lucide-react"

export function RecommendedActions() {
  const actions = [
    {
      id: 1,
      icon: AlertCircle,
      title: "Sell Peloton Stock",
      description: "High volatility detected",
      iconBg: "bg-accent-red/20",
      iconColor: "text-accent-red",
    },
    {
      id: 2,
      icon: TrendingUp,
      title: "Buy Azon Inc.",
      description: "Strong upward trend.",
      iconBg: "bg-accent-green/20",
      iconColor: "text-accent-green",
    },
    {
      id: 3,
      icon: Scale,
      title: "Rebalance Portfolio",
      description: "Tech sector overweight.",
      iconBg: "bg-accent-teal/20",
      iconColor: "text-accent-teal",
    },
  ]

  return (
    <div>
      <h3 className="text-base font-semibold text-white mb-6">Recommended Actions</h3>
      <div className="space-y-4">
        {actions.map((action) => (
          <div key={action.id} className="flex items-center gap-4 group">
            <div className={`w-12 h-12 rounded-lg ${action.iconBg} flex items-center justify-center flex-shrink-0`}>
              <action.icon className={`w-6 h-6 ${action.iconColor}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-white mb-0.5">{action.title}</h4>
              <p className="text-xs text-text-muted">{action.description}</p>
            </div>
            <button className="px-3 py-1.5 sm:px-4 sm:py-2 bg-card border border-border rounded-lg text-xs sm:text-sm font-medium text-white hover:bg-accent-teal/10 hover:border-accent-teal transition-colors flex-shrink-0">
              Review
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
