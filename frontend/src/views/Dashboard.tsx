"use client"
import { motion } from "framer-motion"
import { FreeCashCard } from "@/components/dashboard-ui/free-cash-card"
import { AssetDistributionCard } from "@/components/dashboard-ui/asset-distribution-card"
import { BestPerformingCard } from "@/components/dashboard-ui/best-performing-card"
import { WorstPerformingCard } from "@/components/dashboard-ui/worst-performing-card"
import { PortfolioChartCard } from "@/components/dashboard-ui/portfolio-chart-card"
import { KeyMetricsCard } from "@/components/dashboard-ui/key-metrics-card"
import { MarketNewsCard } from "@/components/dashboard-ui/market-news-card"
import { RecommendedActionsCard } from "@/components/dashboard-ui/recommended-actions-card"

export  function Dashboard() {
  return (
    <div className="min-h-0 bg-background p-6 md:p-8">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-2">Dashboard</h1>
          <p className="text-lg text-text-secondary">Portfolio Details</p>
        </motion.div>

        {/* Top Row - Summary Cards with equal heights */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
          <FreeCashCard />
          <AssetDistributionCard />
          <BestPerformingCard />
          <WorstPerformingCard />
        </div>

        {/* Middle Row - Chart and Metrics with equal heights */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
          <PortfolioChartCard />
          <KeyMetricsCard />
        </div>

        {/* Bottom Row - News and Actions with equal heights */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MarketNewsCard />
          <RecommendedActionsCard />
        </div>
      </div>
    </div>
  )
}
