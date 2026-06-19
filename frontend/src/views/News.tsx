"use client";

import { useState, useEffect } from "react";
import type {
  NewsData,
  PortfolioNewsItem,
  GeneralNewsItem,
  TrendingTopic,
  WatchlistNewsItem,
  RiskType,
  RiskLevel,
} from "../components/news-ui/data/news";
import { PortfolioNewsCard } from "../components/news-ui/components/portfolio-news-card";
import { GeneralNewsCard } from "../components/news-ui/components/general-news-card";
import { TrendingTopics } from "../components/news-ui/components/trending-topics";
import { WatchlistNews } from "../components/news-ui/components/watchlist-news";
import { DailyBriefing } from "../components/news-ui/components/daily-briefing";
import { CategoryFilter } from "../components/news-ui/components/category-filter";
import {
  PortfolioNewsCardSkeleton,
  GeneralNewsCardSkeleton,
  DailyBriefingSkeleton,
  TrendingTopicsSkeleton,
  WatchlistNewsSkeleton,
} from "../components/news-ui/components/news-skeletons";
import {
  fetchClusters,
  fetchSummarizedArticles,
  fetchLatestVideo,
  fetchNewsStats,
  type NewsCluster,
  type SummarizedArticle,
  type VideoMetadata,
  type NewsStats,
} from "../api/news";
import { getWatchlistCompanies } from "../components/news-ui/components/trending-topics";
import { LogIn } from "lucide-react";

// --- Cache Configuration ---
const NEWS_CACHE_KEY = "news_data_cache";
const NEWS_CACHE_EXPIRY_KEY = "news_data_cache_expiry";
const CACHE_DURATION_MS = 30 * 60 * 1000; // 30 minutes

// Empty default data structure
const EMPTY_NEWS_DATA: NewsData = {
  portfolioNews: [],
  generalNews: [],
  trendingTopics: [],
  watchlistNews: [],
  dailyBriefing: {
    title: "Loading...",
    subtitle: "Fetching latest news",
    thumbnailUrl: "/placeholder.svg",
  },
};

// --- Cache Helpers ---
function getCachedNewsData(): NewsData | null {
  try {
    const cached = localStorage.getItem(NEWS_CACHE_KEY);
    const expiry = localStorage.getItem(NEWS_CACHE_EXPIRY_KEY);
    
    if (!cached) return null;
    
    // Check if cache is expired
    if (expiry && Date.now() > parseInt(expiry, 10)) {
      localStorage.removeItem(NEWS_CACHE_KEY);
      localStorage.removeItem(NEWS_CACHE_EXPIRY_KEY);
      return null;
    }
    
    return JSON.parse(cached) as NewsData;
  } catch (error) {
    console.warn("Failed to read news cache:", error);
    return null;
  }
}

function setCachedNewsData(data: NewsData): void {
  try {
    localStorage.setItem(NEWS_CACHE_KEY, JSON.stringify(data));
    localStorage.setItem(NEWS_CACHE_EXPIRY_KEY, String(Date.now() + CACHE_DURATION_MS));
  } catch (error) {
    console.warn("Failed to cache news data:", error);
  }
}

interface NewsDashboardProps {
  data?: NewsData;
}

// --- Helpers ---
function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  return `${Math.floor(diffInSeconds / 86400)}d ago`;
}

function mapFactorToRiskType(factor: string): RiskType {
  const lowerFactor = (factor || "").toLowerCase();
  if (lowerFactor.includes("regulator") || lowerFactor.includes("regulatory"))
    return "Regulatory Risk";
  if (lowerFactor.includes("market")) return "Market Risk";
  if (lowerFactor.includes("operational")) return "Operational Risk";
  if (lowerFactor.includes("volatility")) return "Volatility Risk";
  return "Market Risk";
}

function mapSentimentToRiskLevel(score = 0): RiskLevel {
  const absScore = Math.abs(score);
  if (absScore > 0.7) return "High";
  if (absScore > 0.3) return "Medium";
  return "Low";
}

function mapSentimentLabel(label?: string): "Bullish" | "Bearish" | "Neutral" {
  const lowerLabel = (label || "").toLowerCase();
  if (lowerLabel === "positive" || lowerLabel === "bullish") return "Bullish";
  if (lowerLabel === "negative" || lowerLabel === "bearish") return "Bearish";
  return "Neutral";
}

function mapFactorToCategory(
  factor?: string,
  company?: string
): "Tech" | "Finance" | "Energy" | "All" {
  const lowerFactor = (factor || "").toLowerCase();
  
  // First, check factor_type directly
  if (lowerFactor.includes("tech")) return "Tech";
  if (lowerFactor.includes("energy")) return "Energy";
  if (lowerFactor.includes("financ")) return "Finance";
  
  // Fallback: categorize by company sector
  const lowerCompany = (company || "").toLowerCase();
  
  // Tech companies
  const techCompanies = ["tcs", "infosys", "wipro", "hcltech", "techm", "ltim"];
  if (techCompanies.some(c => lowerCompany.includes(c))) return "Tech";
  
  // Energy companies
  const energyCompanies = ["powergrid", "ntpc", "ongc", "bpcl", "coalindia", "adanigreen", "tatapower"];
  if (energyCompanies.some(c => lowerCompany.includes(c))) return "Energy";
  
  // Finance companies (banks, insurance, finserv)
  const financeCompanies = ["bank", "sbi", "hdfc", "icici", "axis", "kotak", "bajaj", "finserv", "finance", "life"];
  if (financeCompanies.some(c => lowerCompany.includes(c))) return "Finance";
  
  return "All";
}

// Company icon/emoji mapping based on sector
const COMPANY_ICONS: Record<string, string> = {
  // Auto
  "M&M": "🚗",
  "MARUTI": "🚗",
  "TATAMOTORS": "🚗",
  // Steel/Metals
  "JINDALSTEL": "🏗️",
  "TATASTEEL": "🏗️",
  "JSWSTEEL": "🏗️",
  "VEDL": "⛏️",
  "HINDALCO": "⛏️",
  // Banking/Finance
  "SBIN": "🏦",
  "HDFCBANK": "🏦",
  "ICICIBANK": "🏦",
  "AXISBANK": "🏦",
  "KOTAKBANK": "🏦",
  // IT/Tech
  "TCS": "💻",
  "INFY": "💻",
  "WIPRO": "💻",
  "TECHM": "💻",
  "HCLTECH": "💻",
  // Pharma
  "SUNPHARMA": "💊",
  "DRREDDY": "💊",
  "CIPLA": "💊",
  // Energy/Oil
  "RELIANCE": "⚡",
  "ONGC": "🛢️",
  "IOC": "🛢️",
  "BPCL": "🛢️",
  // FMCG
  "HINDUNILVR": "🛒",
  "ITC": "🛒",
  "NESTLEIND": "🍫",
  // Telecom
  "BHARTIARTL": "📱",
  // Default
  "DEFAULT": "📊",
};

function getCompanyIcon(company: string): string {
  return COMPANY_ICONS[company.toUpperCase()] || COMPANY_ICONS["DEFAULT"];
}

function transformStatsToTrendingTopics(stats: NewsStats): TrendingTopic[] {
  if (!stats.by_company || Object.keys(stats.by_company).length === 0) {
    return [];
  }

  // Sort companies by mention count (descending) and take top 4
  const sortedCompanies = Object.entries(stats.by_company)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4);

  return sortedCompanies.map(([company, count], index) => ({
    id: `trending-${index}`,
    label: company,
    trend: "up" as const, // Companies with high mentions are trending up
    icon: getCompanyIcon(company),
    count: count,
  }));
}
function transformClustersToPortfolioNews(
  clusters: NewsCluster[],
  defaultData: NewsData
): PortfolioNewsItem[] {
  if (!clusters || clusters.length === 0) return defaultData.portfolioNews;

  return clusters.map((cluster) => ({
    id: cluster._id || cluster.cluster_id,
    source: cluster.sources?.[0] || "Multiple Sources",
    timeAgo: cluster.published_at ? formatTimeAgo(cluster.published_at) : "",
    title: cluster.title,
    imageUrl: cluster.publishers?.[0]?.icon || "/placeholder.svg",
    url: cluster.urls?.[0] || cluster.publishers?.[0]?.url,
    ticker: {
      symbol: cluster.company ? `$${cluster.company.toUpperCase()}` : "$UNK",
      shortSymbol: cluster.company
        ? `$${cluster.company.charAt(0).toUpperCase()}`
        : "$U",
    },
    risks: [
      {
        type: mapFactorToRiskType(cluster.factor_type || ""),
        level: mapSentimentToRiskLevel(cluster.sentiment_score ?? 0),
      },
    ],
  }));
}

function transformSummarizedToGeneralNews(
  articles: SummarizedArticle[],
  defaultData: NewsData
): GeneralNewsItem[] {
  if (!articles || articles.length === 0) return defaultData.generalNews;

  return articles.map((article) => ({
    id: article.article_id,
    source: article.publisher_name || article.source || "Unknown",
    timeAgo: article.published_at ? formatTimeAgo(article.published_at) : "",
    title: article.title,
    description:
      article.summary || article.content?.slice(0, 200) || article.title,
    imageUrl: article.publisher_icon || "/placeholder.svg",
    sentiment: mapSentimentLabel(article.sentiment_label),
    category: mapFactorToCategory(article.factor_type, article.company),
    url: article.url,
  }));
}

// --- Component ---
export function News({ data }: NewsDashboardProps) {
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [toast, setToast] = useState<{ message: string; visible: boolean }>({
    message: "",
    visible: false,
  });
  
  // Initialize with cached data or empty data
  const [newsDataState, setNewsDataState] = useState<NewsData>(() => {
    const cached = getCachedNewsData();
    return data || cached || EMPTY_NEWS_DATA;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true); // Start as loading
  const [error, setError] = useState<string | null>(null);
// console.log("newsdata state", newsDataState.watchlistNews);

  // Video state
  const [videoData, setVideoData] = useState<VideoMetadata | null>(null);

  // Watchlist refresh trigger
  const [watchlistRefresh, setWatchlistRefresh] = useState(0);

  const categories = ["All", "Tech", "Finance", "Energy"];

  useEffect(() => {
    let cancelled = false;

    const loadNews = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Fetch clusters, summarized articles, video data, and stats in parallel
        const [clusters, summarizedArticles, video, stats] = await Promise.all([
          fetchClusters({ limit: 10 }),
          fetchSummarizedArticles({ limit: 15 }),
          fetchLatestVideo().catch(() => null), // Don't fail if video API is down
          fetchNewsStats().catch(() => null), // Don't fail if stats API is down
        ]);

        if (cancelled) return;

        const fallbackData = data || EMPTY_NEWS_DATA;
        const portfolioNews = transformClustersToPortfolioNews(clusters, fallbackData);
        const generalNews = transformSummarizedToGeneralNews(
          summarizedArticles,
          fallbackData
        );

        // Transform stats to trending topics
        const trendingTopics = stats 
          ? transformStatsToTrendingTopics(stats)
          : [];

        console.log("portfolio news", portfolioNews);

        // Fetch watchlist news for companies in the watchlist
        const watchlistCompanies = getWatchlistCompanies();
        const watchlistNews: WatchlistNewsItem[] = [];
        
        for (const company of watchlistCompanies) {
          // Find relevant articles for this company
          const companyArticles = summarizedArticles.filter(
            (article) => article.company?.toLowerCase() === company.toLowerCase()
          );
          
          if (companyArticles.length > 0) {
            const latestArticle = companyArticles[0];
            watchlistNews.push({
              id: `watchlist-${company}`,
              ticker: company.toUpperCase(),
              headline: latestArticle.summary || latestArticle.title || "No recent news",
              source: latestArticle.publisher_name || latestArticle.source || "Multiple Sources",
              timeAgo: latestArticle.published_at ? formatTimeAgo(latestArticle.published_at) : "Recently",
              url: latestArticle.url,
            });
          } else {
            // No recent articles, show placeholder
            watchlistNews.push({
              id: `watchlist-${company}`,
              ticker: company.toUpperCase(),
              headline: "No recent news available",
              source: "--",
              timeAgo: "--",
              url: undefined,
            });
          }
        }

        // Update video state
        if (video) {
          setVideoData(video);
        }
        console.log('video' , video);
        

        const newNewsData: NewsData = {
          ...fallbackData,
          portfolioNews: portfolioNews.length > 0 ? portfolioNews : fallbackData.portfolioNews,
          generalNews: generalNews.length > 0 ? generalNews : fallbackData.generalNews,
          trendingTopics: trendingTopics.length > 0 ? trendingTopics : fallbackData.trendingTopics,
          watchlistNews: watchlistNews.length > 0 ? watchlistNews : fallbackData.watchlistNews,
        };

        // Cache the fetched data
        setCachedNewsData(newNewsData);
        
        setNewsDataState(newNewsData);
        showToast("Latest news fetched");
      } catch (err) {
        console.error("Failed to fetch news:", err);
        const cached = getCachedNewsData();
        if (cached) {
          setNewsDataState(cached);
          setError("Failed to load latest news — showing cached data");
          showToast("Using cached news data");
        } else {
          setError("Failed to load news. Please try again later.");
          showToast("No cached data available");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    loadNews();

    return () => {
      cancelled = true;
    };
  }, [data, watchlistRefresh]);

  const filteredGeneralNews = newsDataState.generalNews.filter(
    (item: GeneralNewsItem) =>
      activeCategory === "All" ? true : item.category === activeCategory
  );

  const showToast = (message: string) => {
    setToast({ message, visible: true });
    setTimeout(() => setToast({ message: "", visible: false }), 2000);
  };

  const handlePortfolioClick = (item: PortfolioNewsItem) => {
    if (item.url) {
      console.log(" clicked", item);

      window.open(item.url, "_blank", "noopener,noreferrer");
    } else {
      showToast(`No URL available for: ${item.title}`);
    }
  };
  const handleGeneralClick = (item: GeneralNewsItem) =>
    showToast(`Opening: ${item.title}`);
  const handleTopicClick = (topic: TrendingTopic) =>
    showToast(`Searching for ${topic.label}`);
  const handleWatchlistClick = (item: WatchlistNewsItem) =>
    showToast(`Opening ${item.ticker} news`);
  const handleBookmark = (id: string) =>
    showToast(`Bookmark updated for ${id}`);

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-white text-3xl font-bold">News</h1>
          <div className="flex items-center gap-4">
            {isLoading && (
              <span className="text-primary text-sm">Updating...</span>
            )}
            {error && <span className="text-amber-400 text-sm">{error}</span>}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Portfolio News */}
            <section>
              <h2 className="text-primary text-xl font-semibold mb-4">
                Your Portfolio News
              </h2>
              <div className="space-y-4">
                {isLoading && newsDataState.portfolioNews.length === 0 ? (
                  // Show skeletons when loading with no cached data
                  Array.from({ length: 5 }).map((_, index) => (
                    <PortfolioNewsCardSkeleton key={`portfolio-skeleton-${index}`} />
                  ))
                ) : (
                  newsDataState.portfolioNews
                    .slice(0, 5)
                    .map((item: PortfolioNewsItem) => (
                      <PortfolioNewsCard
                        key={item.id}
                        item={item}
                        onClick={handlePortfolioClick}
                        onBookmark={handleBookmark}
                      />
                    ))
                )}
              </div>
            </section>

            {/* General Market News */}
            <section>
              <div className="flex items-center justify-between">
                <h2 className="text-white text-xl font-semibold mb-4">
                  General Market News
                </h2>
                <CategoryFilter
                  categories={categories}
                  activeCategory={activeCategory}
                  onCategoryChange={setActiveCategory}
                />
              </div>
              <div className="space-y-4 mt-2">
                {isLoading && newsDataState.generalNews.length === 0 ? (
                  // Show skeletons when loading with no cached data
                  Array.from({ length: 6 }).map((_, index) => (
                    <GeneralNewsCardSkeleton key={`general-skeleton-${index}`} />
                  ))
                ) : (
                  filteredGeneralNews
                    .slice(0, 6)
                    .map((item: GeneralNewsItem) => (
                      <GeneralNewsCard
                        key={item.id}
                        item={item}
                        onClick={handleGeneralClick}
                        onBookmark={handleBookmark}
                      />
                    ))
                )}
              </div>
            </section>
          </div>

          {/* Right Column - Sidebar */}
          <aside className="space-y-6">
            <section>
              <h2 className="text-white text-xl font-semibold mb-4">
                Daily Briefing
              </h2>
              {isLoading && !videoData ? (
                <DailyBriefingSkeleton />
              ) : (
                <DailyBriefing
                  briefing={{
                    ...newsDataState.dailyBriefing,
                    title: videoData?.title || newsDataState.dailyBriefing.title,
                    subtitle:
                      videoData?.subtitle || newsDataState.dailyBriefing.subtitle,
                    thumbnailUrl:
                      videoData?.thumbnail_url ||
                      newsDataState.dailyBriefing.thumbnailUrl,
                    // Use fixed captions endpoint when captions_vtt exists in metadata
                    captionsUrl: videoData?.captions_vtt ? "/api/video/captions" : undefined,
                  }}
                  videoUrl={videoData?.video_url}
                  videoStatus={videoData?.status}
                  onPlay={() => showToast("Playing daily briefing...")}
                />
              )}
            </section>

            {isLoading && newsDataState.trendingTopics.length === 0 ? (
              <TrendingTopicsSkeleton />
            ) : (
              <TrendingTopics
                topics={newsDataState.trendingTopics}
                onTopicClick={handleTopicClick}
                onAddToWatchlist={(company) => {
                  showToast(`${company} added to watchlist`);
                  setWatchlistRefresh((prev) => prev + 1);
                }}
              />
            )}

            {isLoading && newsDataState.watchlistNews.length === 0 ? (
              <WatchlistNewsSkeleton />
            ) : (
              <WatchlistNews
                items={newsDataState.watchlistNews}
                onItemClick={handleWatchlistClick}
                onToggleAlert={(item) =>
                  showToast(`Alert ${item.ticker} updated`)
                }
              />
            )}
          </aside>
        </div>
      </div>

      <div
        className={`fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 bg-primary text-white rounded-lg shadow-lg transition-all duration-300 ${
          toast.visible
            ? "opacity-100 translate-y-0"
            : "opacity-0 translate-y-4 pointer-events-none"
        }`}
      >
        {toast.message}
      </div>
    </div>
  );
}
