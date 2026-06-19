"use client"

import { CommodityHeader } from "../components/commodities/commodity-header"
import { MarketPriceCard } from "../components/commodities/market-price-card"
import { HoldingsCard } from "../components/commodities/holdings-card"
import { KeyStatsCard } from "../components/commodities/key-stats-card"
import { PriceChart } from "../components/commodities/price-chart"
import { NewsCard } from "../components/commodities/news-card"
import { MarketContextCard } from "../components/commodities/market-context-card"
import { RiskTrackingCard } from "../components/commodities/risk-tracking-card"
import { commodityData } from "../components/commodities/data/commodity-data"
import { useAsset } from "@/context/AssetContext"

export function CommoditiesDashboard() {
  const { selectedAsset } = useAsset()
  
  // Create dynamic commodity data from selected asset or use default
  const dynamicData = selectedAsset && selectedAsset.assetType === 'commodities'
    ? {
        symbol: selectedAsset.ticker,
        name: selectedAsset.name,
        marketPrice: {
          currentPrice: selectedAsset.pricePerOz || commodityData.marketPrice.currentPrice,
          change24h: {
            value: selectedAsset.change || commodityData.marketPrice.change24h.value,
            percentage: selectedAsset.changePercent || commodityData.marketPrice.change24h.percentage,
            isPositive: (selectedAsset.change || 0) >= 0,
          },
        },
        holdings: {
          ...commodityData.holdings,
          avgBuyPrice: (selectedAsset.pricePerOz || commodityData.marketPrice.currentPrice) * 0.92,
        },
        keyStats: {
          open: (selectedAsset.pricePerOz || commodityData.keyStats.open) * 0.99,
          high: (selectedAsset.pricePerOz || commodityData.keyStats.high) * 1.02,
          low: (selectedAsset.pricePerOz || commodityData.keyStats.low) * 0.98,
          volume: commodityData.keyStats.volume,
          marketCap: commodityData.keyStats.marketCap,
          weekHigh52: (selectedAsset.pricePerOz || commodityData.keyStats.weekHigh52) * 1.05,
        },
        chartData: commodityData.chartData,
        news: commodityData.news,
        marketContext: `${selectedAsset.name} is currently trading at $${selectedAsset.pricePerOz?.toLocaleString('en-US', { minimumFractionDigits: 2 })} per oz with a ${(selectedAsset.changePercent || 0) >= 0 ? 'positive' : 'negative'} change of ${selectedAsset.changePercent?.toFixed(2)}%. ` + commodityData.marketContext,
        riskTracking: commodityData.riskTracking,
      }
    : commodityData

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      <div className="max-w-[1400px] mx-auto space-y-6">
        {/* Header */}
        <CommodityHeader symbol={dynamicData.symbol} name={dynamicData.name} />

        {/* Top Row - Three Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <MarketPriceCard data={dynamicData.marketPrice} />
          <HoldingsCard data={dynamicData.holdings} />
          <KeyStatsCard data={dynamicData.keyStats} />
        </div>

        {/* Chart Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PriceChart data={dynamicData.chartData} />
          <NewsCard news={dynamicData.news} />
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MarketContextCard text={dynamicData.marketContext} />
          <RiskTrackingCard data={dynamicData.riskTracking} />
        </div>
      </div>
    </div>
  )
}
