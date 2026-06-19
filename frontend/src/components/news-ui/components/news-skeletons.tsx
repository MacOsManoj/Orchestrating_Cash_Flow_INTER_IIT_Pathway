"use client"

import { Skeleton } from "@/components/ui/skeleton"

// Skeleton for Portfolio News Card
export function PortfolioNewsCardSkeleton() {
  return (
    <div className="bg-card rounded-xl p-4 flex gap-4 border border-border">
      {/* Image placeholder */}
      <Skeleton className="w-32 h-24 rounded-lg flex-shrink-0" />
      
      <div className="flex flex-col gap-2 flex-1">
        {/* Source and time */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-32" />
        </div>
        
        {/* Title */}
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-3/4" />
        
        {/* Ticker and risk badges */}
        <div className="flex items-center gap-2 mt-auto">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
      </div>
    </div>
  )
}

// Skeleton for General News Card
export function GeneralNewsCardSkeleton() {
  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <div className="flex gap-4">
        <div className="flex-1">
          {/* Source and time */}
          <div className="flex items-center justify-between mb-2">
            <Skeleton className="h-4 w-40" />
          </div>
          
          {/* Title */}
          <Skeleton className="h-5 w-full mb-2" />
          <Skeleton className="h-5 w-5/6 mb-3" />
          
          {/* Description */}
          <Skeleton className="h-4 w-full mb-1" />
          <Skeleton className="h-4 w-4/5 mb-3" />
          
          {/* Category and sentiment */}
          <div className="flex items-center gap-2">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
        
        {/* Image placeholder */}
        <Skeleton className="w-32 h-24 rounded-lg flex-shrink-0" />
      </div>
    </div>
  )
}

// Skeleton for Daily Briefing
export function DailyBriefingSkeleton() {
  return (
    <div className="bg-card rounded-xl overflow-hidden border border-border">
      {/* Video thumbnail placeholder */}
      <Skeleton className="w-full h-48" />
      
      <div className="p-4">
        {/* Title */}
        <Skeleton className="h-5 w-3/4 mb-2" />
        {/* Subtitle */}
        <Skeleton className="h-4 w-full mb-1" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  )
}

// Skeleton for Trending Topics
export function TrendingTopicsSkeleton() {
  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <Skeleton className="h-6 w-36 mb-4" />
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="flex items-center gap-3 p-2">
            <Skeleton className="w-6 h-6 rounded-full" />
            <Skeleton className="w-5 h-5" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-5 w-12 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  )
}

// Skeleton for Watchlist News
export function WatchlistNewsSkeleton() {
  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <Skeleton className="h-6 w-32 mb-4" />
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="p-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="w-6 h-6 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
