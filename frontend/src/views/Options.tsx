"use client"

import { StockHeader } from "../components/options-ui/stock-header"
import { KeyMetrics } from "../components/options-ui/key-metrics"
import { OptionsChainFilters } from "../components/options-ui/options-chain-filters"
import { OptionsChainTable } from "../components/options-ui/options-chain-table"
import { GreeksOverview } from "../components/options-ui/greeks-overview"
import { MarketSentimentPanel } from "../components/options-ui/market-sentiment-panel"
import { NewsAnalytics } from "../components/options-ui/news-analytics"
import { PayoffSimulator } from "../components/options-ui/payoff-simulator"

export function Options() {
  return (
    <div className="min-h-screen bg-[#0f1f1e] text-white p-4 md:p-6 lg:p-8">
      <div className="max-w-[1400px] mx-auto space-y-6">
        {/* Stock Header */}
        <StockHeader />

        {/* Key Metrics */}
        <KeyMetrics />

        {/* Options Chain Section */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-white">Options chain</h2>

          {/* Filters */}
          <OptionsChainFilters />

          {/* Grid Layout */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {/* Options Table */}
            <div className="xl:col-span-2">
              <OptionsChainTable />
            </div>

            {/* Side Panels */}
            <div className="space-y-4">
              <GreeksOverview />
              <MarketSentimentPanel />
            </div>
          </div>
        </div>

        {/* Bottom Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <NewsAnalytics />
          <PayoffSimulator />
        </div>
      </div>
    </div>
  )
}
