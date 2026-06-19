import type { NewsItem } from "../data/stock-data"

interface RecentNewsSectionProps {
  news: NewsItem[]
  updatedTime?: string
}

export function RecentNewsSection({ news, updatedTime = "49 min ago" }: RecentNewsSectionProps) {
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-white">Recent news about asset:</h3>
        <span className="text-sm text-gray-400">Updated {updatedTime}</span>
      </div>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {news.map((item) => (
          <div key={item.id} className="flex-shrink-0 w-48 h-32 border border-teal-700/50 rounded-lg bg-[#0a2428] p-4">
            {item.title ? (
              <div>
                <h4 className="text-sm font-medium text-white mb-2">{item.title}</h4>
                <p className="text-xs text-gray-400">{item.description}</p>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-xs">News placeholder</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
