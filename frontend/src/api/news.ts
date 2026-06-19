// Base URLs (use Vite env vars if provided; fall back to sensible defaults)
export const NEWS_API_BASE_URL = import.meta.env.VITE_NEWS_API_BASE_URL || "http://localhost:8000";

// VIDEO_API_BASE_URL: Frontend calls this to reach the video endpoints (e.g. /api/video/latest).
// For local development use `http://localhost:8000`. In production set `VITE_VIDEO_API_BASE_URL`
// to your deployed backend (example: "http://136.119.40.138:8000").
// export const VIDEO_API_BASE_URL = import.meta.env.VITE_VIDEO_API_BASE_URL || (import.meta.env.PROD ? "http://136.119.40.138:8000" : "http://localhost:8000");
export const VIDEO_API_BASE_URL = "http://localhost:8000";

export interface Publisher {
  name: string;
  icon: string;
  url: string;
  source: string;
  published_at: string;
  title_normalized: string;
}

export interface NewsCluster {
  _id: string;
  cluster_id: string;
  title: string;
  company: string;
  factor_type: string;
  published_at: string;
  sources: string[];
  urls: string[];
  publishers: Publisher[];
  article_count: number;
  sentiment_label: string;
  sentiment_score: number;
  liquidity_impact: string;
}

export interface FetchClustersOptions {
  company?: string;
  factor_type?: string;
  start_date?: string;
  limit?: number;
  skip?: number;
}

export async function fetchClusters(
  options: FetchClustersOptions = {}
): Promise<NewsCluster[]> {
  const { company, factor_type, start_date, limit = 50, skip = 0 } = options;

  const params = new URLSearchParams();
  if (company) params.append("company", company);
  if (factor_type) params.append("factor_type", factor_type);
  if (start_date) params.append("start_date", start_date);
  params.append("limit", limit.toString());
  params.append("skip", skip.toString());

  const response = await fetch(
    `${NEWS_API_BASE_URL}/api/news/clusters?${params.toString()}`,
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}

// --- Summarized Articles ---
export interface SummarizedArticle {
  article_id: string;
  title: string;
  url: string;
  company: string;
  factor_type: string;
  published_at: string;
  source: string;
  content: string;
  content_length: number;
  publisher_name: string;
  author: string;
  publisher_icon: string;
  sentiment_label: string;
  sentiment_score: number;
  liquidity_impact: string;
  critical_events: string;
  decisions: string;
  cluster_id: string;
  enriched_at: string;
  is_relevant: boolean;
  relevance_reason: string;
  summary: string;
  key_points: string[];
  financial_metrics: Record<string, unknown>;
  impact_assessment: string;
  summarized_at: string;
  worker_id: string;
}

export interface FetchSummarizedOptions {
  company?: string;
  factor_type?: string;
  sentiment?: string;
  liquidity_impact?: string;
  start_date?: string;
  end_date?: string;
  source?: string;
  is_relevant?: boolean;
  limit?: number;
  skip?: number;
}

export async function fetchSummarizedArticles(
  options: FetchSummarizedOptions = {}
): Promise<SummarizedArticle[]> {
  const {
    company,
    factor_type,
    sentiment,
    liquidity_impact,
    start_date,
    end_date,
    source,
    is_relevant,
    limit = 50,
    skip = 0,
  } = options;

  const params = new URLSearchParams();
  if (company) params.append("company", company);
  if (factor_type) params.append("factor_type", factor_type);
  if (sentiment) params.append("sentiment", sentiment);
  if (liquidity_impact) params.append("liquidity_impact", liquidity_impact);
  if (start_date) params.append("start_date", start_date);
  if (end_date) params.append("end_date", end_date);
  if (source) params.append("source", source);
  if (is_relevant !== undefined)
    params.append("is_relevant", is_relevant.toString());
  params.append("limit", limit.toString());
  params.append("skip", skip.toString());

  const response = await fetch(
    `${NEWS_API_BASE_URL}/api/news/summarized?${params.toString()}`,
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}

// --- Video API ---
export interface VideoMetadata {
  video_url: string | null;
  thumbnail_url: string | null;
  captions_vtt: string | null;
  title: string;
  subtitle: string;
  generated_at: string | null;
  status: "pending" | "generating" | "completed" | "failed";
  error: string | null;
}

export async function fetchLatestVideo(): Promise<VideoMetadata> {
  const response = await fetch(`${VIDEO_API_BASE_URL}/api/video/latest`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Video API Error: ${response.status}`);
  }

  return response.json();
}

export async function triggerVideoGeneration(
  force: boolean = false
): Promise<{ message: string; status?: string }> {
  const response = await fetch(`${VIDEO_API_BASE_URL}/api/video/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ force }),
  });

  if (!response.ok) {
    throw new Error(`Video API Error: ${response.status}`);
  }

  return response.json();
}

// --- News Stats API ---
export interface NewsStats {
  total_enriched: number;
  total_summarized: number;
  total_clusters: number;
  by_company: Record<string, number>;
  by_sentiment: {
    negative: number;
    neutral: number;
    positive: number;
  };
  today_count: number;
}

export async function fetchNewsStats(): Promise<NewsStats> {
  const response = await fetch(`${NEWS_API_BASE_URL}/api/news/stats`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}
