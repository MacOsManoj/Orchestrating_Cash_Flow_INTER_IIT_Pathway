import { TrendingUp, Building2 } from "lucide-react"

interface NewsItem {
  id: string
  title: string
  source: string
  time: string
  icon: string
}

interface NewsCardProps {
  news: NewsItem[]
}

export function NewsCard({ news }: NewsCardProps) {
  const getIcon = (iconType: string) => {
    switch (iconType) {
      case "chart":
        return <TrendingUp className="h-6 w-6" />
      case "building":
        return <Building2 className="h-6 w-6" />
      default:
        return null
    }
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-6">News and analytics</h3>

      <div className="space-y-4">
        {news.map((item) => (
          <div key={item.id} className="flex items-start gap-4 p-4 rounded-lg bg-background border border-border">
            <div className="bg-card rounded-lg p-3 flex items-center justify-center text-success">
              {getIcon(item.icon)}
            </div>

            <div className="flex-1">
              <h4 className="text-sm font-medium text-white mb-2 leading-relaxed">{item.title}</h4>
              <p className="text-xs text-white/70">
                {item.source} • {item.time}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
