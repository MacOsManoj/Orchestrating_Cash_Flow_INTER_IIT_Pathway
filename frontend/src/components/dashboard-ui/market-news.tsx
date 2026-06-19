import { TrendingUp, Building2, Landmark } from "lucide-react"

export function MarketNews() {
  const newsItems = [
    {
      id: 1,
      icon: TrendingUp,
      title: "Tech stocks rally on positive inflation data",
      time: "2 hours ago",
      source: "Reuters",
      iconBg: "bg-accent-teal/20",
      iconColor: "text-accent-teal",
    },
    {
      id: 2,
      icon: Building2,
      title: "Oil prices surge as OPEC+ announces production cuts",
      time: "5 hours ago",
      source: "Bloomberg",
      iconBg: "bg-accent-blue/20",
      iconColor: "text-accent-blue",
    },
    {
      id: 3,
      icon: Landmark,
      title: "Federal Reserve hints at interest rate stability for Q3",
      time: "8 hours ago",
      source: "Wall Street Journal",
      iconBg: "bg-accent-purple/20",
      iconColor: "text-accent-purple",
    },
  ]

  return (
    <div>
      <h3 className="text-base font-semibold text-white mb-6">Market News</h3>
      <div className="space-y-4">
        {newsItems.map((item) => (
          <div key={item.id} className="flex gap-4 group cursor-pointer">
            <div
              className={`w-16 h-16 rounded-lg ${item.iconBg} flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform`}
            >
              <item.icon className={`w-8 h-8 ${item.iconColor}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-white mb-1 group-hover:text-accent-teal transition-colors">
                {item.title}
              </h4>
              <p className="text-xs text-text-muted">
                {item.time} · {item.source}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
