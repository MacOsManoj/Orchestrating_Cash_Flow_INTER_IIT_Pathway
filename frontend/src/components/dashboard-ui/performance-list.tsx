interface PerformanceItem {
  id: number
  name: string
  category: string
  change: string
  value: string
  positive: boolean
  badge: string
  badgeColor: string
}

interface PerformanceListProps {
  title: string
  items: PerformanceItem[]
}

export function PerformanceList({ title, items }: PerformanceListProps) {
  return (
    <div>
      <h3 className="text-base font-semibold text-white mb-4">{title}</h3>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full ${item.badgeColor} flex items-center justify-center flex-shrink-0`}>
              <span className="text-xs font-bold text-background">{item.badge}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{item.name}</p>
              <p className="text-xs text-text-muted">{item.category}</p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className={`text-sm font-semibold ${item.positive ? "text-accent-green" : "text-accent-red"}`}>
                {item.change}
              </p>
              <p className="text-xs text-white">{item.value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
