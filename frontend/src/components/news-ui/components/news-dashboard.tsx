"use client"

import { useState } from "react"
import type { NewsData, PortfolioNewsItem, GeneralNewsItem, TrendingTopic, WatchlistNewsItem } from "../data/news"
import { PortfolioNewsCard } from "./portfolio-news-card"
import { GeneralNewsCard } from "./general-news-card"
import { TrendingTopics } from "./trending-topics"
import { WatchlistNews } from "./watchlist-news"
import { DailyBriefing } from "./daily-briefing"
import { CategoryFilter } from "./category-filter"

interface NewsDashboardProps {
  data: NewsData
}

export function NewsDashboard({ data }: NewsDashboardProps) {
  const [activeCategory, setActiveCategory] = useState("All")
  const [toast, setToast] = useState<{ message: string; visible: boolean }>({ message: "", visible: false })
  const categories = ["All", "Tech", "Finance", "Energy"]

  const filteredGeneralNews = data.generalNews.filter(
    (item) => activeCategory === "All" || item.category === activeCategory,
  )

  const showToast = (message: string) => {
    setToast({ message, visible: true })
    setTimeout(() => setToast({ message: "", visible: false }), 2000)
  }

  const handlePortfolioClick = (item: PortfolioNewsItem) => {
    showToast(`Opening: ${item.title}`)
  }

  const handleGeneralClick = (item: GeneralNewsItem) => {
    showToast(`Opening: ${item.title}`)
  }

  const handleTopicClick = (topic: TrendingTopic) => {
    showToast(`Searching for ${topic.label}`)
  }

  const handleWatchlistClick = (item: WatchlistNewsItem) => {
    showToast(`Opening ${item.ticker} news`)
  }

  const handleBookmark = (id: string) => {
    showToast(`Bookmark updated for ${id}`)
  }

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-white text-3xl font-bold mb-6">News</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Portfolio News */}
            <section>
              <h2 className="text-teal-400 text-xl font-semibold mb-4">Your Portfolio News</h2>
              <div className="space-y-4">
                {data.portfolioNews.map((item) => (
                  <PortfolioNewsCard
                    key={item.id}
                    item={item}
                    onClick={handlePortfolioClick}
                    onBookmark={handleBookmark}
                  />
                ))}
              </div>
            </section>

            {/* General Market News */}
            <section>
              <h2 className="text-white text-xl font-semibold mb-4">General Market News</h2>
              <CategoryFilter
                categories={categories}
                activeCategory={activeCategory}
                onCategoryChange={setActiveCategory}
              />
              <div className="space-y-4 mt-4">
                {filteredGeneralNews.map((item) => (
                  <GeneralNewsCard key={item.id} item={item} onClick={handleGeneralClick} onBookmark={handleBookmark} />
                ))}
              </div>
            </section>
          </div>

          {/* Right Column - Sidebar */}
          <div className="space-y-6">
            {/* Daily Briefing */}
            <section>
              <h2 className="text-white text-xl font-semibold mb-4">Daily Briefing</h2>
              <DailyBriefing briefing={data.dailyBriefing} onPlay={() => showToast("Playing briefing...")} />
            </section>

            {/* Trending Topics */}
            <TrendingTopics
              topics={data.trendingTopics}
              onTopicClick={handleTopicClick}
              onFollow={(topic) => showToast(`Following ${topic.label}`)}
            />

            {/* Watchlist News */}
            <WatchlistNews
              items={data.watchlistNews}
              onItemClick={handleWatchlistClick}
              onToggleAlert={(item) => showToast(`Alert ${item.ticker} updated`)}
            />
          </div>
        </div>
      </div>

      <div
        className={`fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 bg-teal-500 text-white rounded-lg shadow-lg transition-all duration-300 ${
          toast.visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"
        }`}
      >
        {toast.message}
      </div>
    </div>
  )
}
