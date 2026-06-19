"use client"

import React from "react"
import { Calendar, ExternalLink, Search, X, Plus, Check, Loader2 } from "lucide-react"
import { useAsset } from "@/context/AssetContext"
import { useBondDetails, usePriceStatistics, useSummarizedNews, useBondSearch } from "@/queries/bonds_queries"
import { BondCompare } from "./BondCompare"
import { BondChat } from "@/components/BondChat"
import { executeTrade, type TradeRequest } from "@/api/portfolio"
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from "recharts"

// ============================================================================
// TRADE MODAL COMPONENT
// ============================================================================

interface TradeModalProps {
  isOpen: boolean
  onClose: () => void
  tradeType: "buy" | "sell"
  ticker: string
  assetName: string
  currentPrice: number
  onExecute: (quantity: number) => Promise<void>
  isLoading: boolean
}

const TradeModal: React.FC<TradeModalProps> = ({
  isOpen,
  onClose,
  tradeType,
  ticker,
  assetName,
  currentPrice,
  onExecute,
  isLoading,
}) => {
  const [quantity, setQuantity] = React.useState<string>("1")
  const [error, setError] = React.useState<string>("")

  const totalValue = parseFloat(quantity || "0") * currentPrice

  const handleSubmit = async () => {
    const qty = parseFloat(quantity)
    if (isNaN(qty) || qty <= 0) {
      setError("Please enter a valid quantity")
      return
    }
    setError("")
    await onExecute(qty)
    setQuantity("1")
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-md animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className={`text-xl font-semibold ${tradeType === "buy" ? "text-green-500" : "text-red-500"}`}>
            {tradeType === "buy" ? "Buy" : "Sell"} Bond
          </h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Asset Info */}
          <div className="bg-background/50 rounded-lg p-3">
            <p className="text-sm text-white/60">Bond</p>
            <p className="font-semibold">{assetName}</p>
            <p className="text-xs text-white/40 mt-1">ISIN: {ticker}</p>
          </div>

          {/* Current Price */}
          <div className="bg-background/50 rounded-lg p-3">
            <p className="text-sm text-white/60">Current Price (% of Par)</p>
            <p className="font-semibold text-lg">₹{currentPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</p>
          </div>

          {/* Quantity Input */}
          <div>
            <label className="block text-sm text-white/60 mb-2">Face Value (₹)</label>
            <input
              type="number"
              min="1000"
              step="1000"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary"
              placeholder="Enter face value amount"
            />
            {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
          </div>

          {/* Total Value */}
          <div className="bg-background/50 rounded-lg p-3">
            <p className="text-sm text-white/60">Total Investment</p>
            <p className="font-bold text-xl">
              ₹{totalValue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border flex gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-border rounded-lg text-white/70 hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50 ${
              tradeType === "buy"
                ? "bg-green-500 hover:bg-green-600 text-white"
                : "bg-red-500 hover:bg-red-600 text-white"
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              `Confirm ${tradeType === "buy" ? "Buy" : "Sell"}`
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// SKELETON COMPONENTS
// ============================================================================

const SkeletonPulse: React.FC<{ className?: string }> = ({ className = "" }) => (
  <div className={`bg-[#1e3a5f] rounded animate-pulse ${className}`} />
)

const BondHeaderSkeleton: React.FC = () => (
  <div className="flex items-start justify-between mb-6">
    <div>
      <SkeletonPulse className="h-9 w-96 mb-2" />
      <SkeletonPulse className="h-4 w-80" />
    </div>
    <div className="flex gap-3">
      <SkeletonPulse className="h-12 w-24 rounded-lg" />
      <SkeletonPulse className="h-12 w-24 rounded-lg" />
      <SkeletonPulse className="h-12 w-28 rounded-lg" />
    </div>
  </div>
)

const CouponCardSkeleton: React.FC = () => (
  <div className="bg-card border border-border rounded-xl p-6">
    <div className="grid grid-cols-2 gap-4 mb-4">
      <div>
        <SkeletonPulse className="h-4 w-20 mb-2" />
        <SkeletonPulse className="h-9 w-24 mb-1" />
        <SkeletonPulse className="h-4 w-28" />
      </div>
      <div>
        <SkeletonPulse className="h-4 w-24 mb-2" />
        <SkeletonPulse className="h-8 w-28" />
      </div>
    </div>
    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
      <div>
        <SkeletonPulse className="h-4 w-28 mb-2" />
        <SkeletonPulse className="h-6 w-24" />
      </div>
      <div>
        <SkeletonPulse className="h-4 w-32 mb-2" />
        <SkeletonPulse className="h-6 w-20" />
        <SkeletonPulse className="h-3 w-36 mt-1" />
      </div>
    </div>
  </div>
)

const PriceCardSkeleton: React.FC = () => (
  <div className="bg-card border border-border rounded-xl p-6">
    <div className="mb-4">
      <div className="flex items-baseline justify-between mb-2">
        <SkeletonPulse className="h-4 w-20" />
        <div className="text-right">
          <SkeletonPulse className="h-3 w-12 mb-1" />
          <SkeletonPulse className="h-4 w-20" />
        </div>
      </div>
      <div className="flex items-baseline gap-3">
        <SkeletonPulse className="h-10 w-24" />
        <SkeletonPulse className="h-4 w-16" />
        <div className="ml-auto">
          <SkeletonPulse className="h-3 w-12 mb-1" />
          <SkeletonPulse className="h-3 w-10 mb-1" />
          <SkeletonPulse className="h-4 w-8" />
        </div>
      </div>
    </div>
    <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
      {[1, 2, 3].map((i) => (
        <div key={i}>
          <SkeletonPulse className="h-3 w-20 mb-2" />
          <SkeletonPulse className="h-5 w-16" />
        </div>
      ))}
    </div>
  </div>
)

const RiskMetricsSkeleton: React.FC = () => (
  <div className="bg-card border border-border rounded-xl p-6">
    <SkeletonPulse className="h-5 w-28 mb-4" />
    <div className="grid grid-cols-3 gap-4">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i}>
          <SkeletonPulse className="h-3 w-16 mb-2" />
          <SkeletonPulse className="h-4 w-20" />
        </div>
      ))}
    </div>
  </div>
)

const ChartSkeleton: React.FC = () => (
  <div className="col-span-2 bg-card border border-border rounded-xl p-6">
    <div className="flex gap-2 mb-4">
      {[1, 2, 3, 4, 5].map((i) => (
        <SkeletonPulse key={i} className="h-8 w-12" />
      ))}
    </div>
    <SkeletonPulse className="h-64 w-full mb-4" />
    <div className="grid grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i}>
          <SkeletonPulse className="h-3 w-24 mb-2" />
          <SkeletonPulse className="h-6 w-16" />
        </div>
      ))}
    </div>
  </div>
)

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

// Extract ISIN from asset (handles different formats)
function extractIsin(asset: { ticker?: string; id?: string } | null): string | undefined {
  if (!asset) return undefined
  // If ticker looks like an ISIN (starts with IN or 2 letter country code), use it
  if (asset.ticker && asset.ticker.startsWith("IN")) {
    return asset.ticker
  }
  // If id contains bond- prefix, extract the ISIN part
  if (asset.id && asset.id.startsWith("bond-")) {
    return asset.id.replace("bond-", "")
  }
  return asset.ticker || undefined
}

// Format coupon rate as percentage string
function formatCouponRate(rate: number | undefined | null): string {
  if (rate === undefined || rate === null) return "N/A"
  const percentage = rate < 1 ? rate * 100 : rate
  return `${percentage.toFixed(2)}%`
}

// Format date for display
function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return "N/A"
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" })
  } catch {
    return dateStr
  }
}

// Data structures
interface PortfolioImpact {
  allocation: string
  portfolioYieldDelta: string
}

interface CashFlowRow {
  paymentDate: string
  type: string
  couponPercent: number
  days: number
  principal: string
  totalPayment: string
}

const ALL_CASH_FLOW_DATA: CashFlowRow[] = [
  {
    paymentDate: "2025-04-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 183,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2025-10-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 182,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2026-04-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 183,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2026-10-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 182,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2027-04-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 183,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2027-10-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 182,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2028-04-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 183,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2040-04-15",
    type: "Coupon",
    couponPercent: 8.5,
    days: 183,
    principal: "$0.00",
    totalPayment: "$42.50",
  },
  {
    paymentDate: "2040-10-15",
    type: "Coupon + Principal",
    couponPercent: 8.5,
    days: 183,
    principal: "$1,000",
    totalPayment: "$1,042.50",
  },
]

const PORTFOLIO_IMPACT: PortfolioImpact = {
  allocation: "2.5%",
  portfolioYieldDelta: "+0.03%",
}

const SUMMARY_TEXT =
  "This bond offers a fixed coupon with its associated credit risk profile. Its duration makes it rate-sensitive, while spreads reflect the current credit quality. Key risks arise from yield curve volatility and market headlines influencing spreads and VaR exposure."

// Main Component
export const Bonds: React.FC = () => {
  const { selectedAsset } = useAsset()
  const [selectedTimeFilter, setSelectedTimeFilter] = React.useState("All")
  const [selectedTypeFilter, setSelectedTypeFilter] = React.useState("All Types")
  const [dateRange, setDateRange] = React.useState<{ start: string; end: string } | null>(null)
  const [showDatePicker, setShowDatePicker] = React.useState(false)
  
  // Chart time period state
  const timePeriods = ["1M", "3M", "1Y", "MAX"]
  const [selectedTimePeriod, setSelectedTimePeriod] = React.useState("MAX")

  // Compare modal state
  const [showCompareModal, setShowCompareModal] = React.useState(false)
  const [compareSearchQuery, setCompareSearchQuery] = React.useState("")
  const [selectedBondsForCompare, setSelectedBondsForCompare] = React.useState<string[]>([])
  const [showCompareView, setShowCompareView] = React.useState(false)

  // Trade modal state
  const [tradeModalOpen, setTradeModalOpen] = React.useState(false)
  const [tradeType, setTradeType] = React.useState<"buy" | "sell">("buy")
  const [isTrading, setIsTrading] = React.useState(false)
  const [tradeMessage, setTradeMessage] = React.useState<{ type: "success" | "error"; text: string } | null>(null)

  // Search for bonds to compare
  const { data: searchResults, isLoading: isSearching } = useBondSearch(compareSearchQuery)

  // Extract ISIN from selected asset
  const isin = extractIsin(selectedAsset)

  // Fetch bond details from API
  const { data: bondDetails, isLoading: isLoadingDetails, error: detailsError } = useBondDetails(isin)

  // Bond header info
  const bondName = bondDetails?.bond_name || selectedAsset?.name || "Select a bond to view details"

  // Derive search term from bond name (take text before first digit)
  const searchTerm = React.useMemo(() => {
    if (!bondName || bondName === "Select a bond to view details") return "Indian Bonds"
    const match = bondName.match(/^([^\d]+)/)
    return match ? match[1].trim() : bondName
  }, [bondName])

  // Fetch price forecast data for chart
  const { data: priceStats, isLoading: isLoadingPrice } = usePriceStatistics(isin, selectedTimePeriod as any)

  // Fetch news articles
  const { data: newsArticles, isLoading: isLoadingNews } = useSummarizedNews(searchTerm, 5)

  // Add current bond to compare list when modal opens
  React.useEffect(() => {
    if (showCompareModal && isin && !selectedBondsForCompare.includes(isin)) {
      setSelectedBondsForCompare([isin])
    }
  }, [showCompareModal, isin])

  // Handle adding/removing bonds from compare list
  const toggleBondForCompare = (bondIsin: string) => {
    setSelectedBondsForCompare(prev => 
      prev.includes(bondIsin)
        ? prev.filter(b => b !== bondIsin)
        : [...prev, bondIsin]
    )
  }

  // Handle opening compare view
  const handleOpenCompareView = () => {
    if (selectedBondsForCompare.length >= 2) {
      setShowCompareModal(false)
      setShowCompareView(true)
    }
  }

  // Handle closing compare view
  const handleCloseCompareView = () => {
    setShowCompareView(false)
  }

  // Handle removing bond from compare view
  const handleRemoveBondFromCompare = (bondIsin: string) => {
    setSelectedBondsForCompare(prev => prev.filter(b => b !== bondIsin))
    if (selectedBondsForCompare.length <= 2) {
      setShowCompareView(false)
    }
  }

  // Handle trade modal
  const handleOpenTradeModal = (type: "buy" | "sell") => {
    setTradeType(type)
    setTradeModalOpen(true)
    setTradeMessage(null)
  }

  const handleExecuteTrade = async (quantity: number) => {
    setIsTrading(true)
    try {
      const tradeRequest: TradeRequest = {
        asset_type: "bonds",
        ticker: bondIsin,
        action: tradeType,
        quantity: quantity,
        price: lastPrice || 100,
        asset_name: bondName,
      }

      const response = await executeTrade(tradeRequest)
      setTradeMessage({ type: "success", text: response.message })
      setTradeModalOpen(false)
      
      // Show success notification for 3 seconds
      setTimeout(() => setTradeMessage(null), 3000)
    } catch (error: any) {
      setTradeMessage({ type: "error", text: error.message || "Trade failed" })
    } finally {
      setIsTrading(false)
    }
  }

  // Show loading state
  const isLoading = isLoadingDetails

  // ============================================================================
  // DERIVED DATA FROM API
  // ============================================================================

  const bondIsin = bondDetails?.isin || isin || "N/A"
  const creditRating = bondDetails?.credit_rating || "N/A"

  // Coupon info
  const couponRate = formatCouponRate(bondDetails?.coupon_rate)
  const maturityDate = formatDate(bondDetails?.maturity_date)
  const nextCouponDate = formatDate(bondDetails?.next_coupon_date)
  const minimumIncrement = bondDetails?.minimum_increment ? `₹${bondDetails.minimum_increment.toLocaleString()}` : "N/A"

  // Price info
  const lastPrice = bondDetails?.last_price ?? 0
  const cleanPrice = bondDetails?.clean_price ?? 0
  const dirtyPrice = cleanPrice + (bondDetails?.accrued_interest ?? 0)
  const accruedInterest = bondDetails?.accrued_interest ?? 0
  const bidPrice = lastPrice - 0.3
  const askPrice = lastPrice + 0.3
  const spread = 0.6

  // Risk metrics
  const duration = bondDetails?.duration ? `${bondDetails.duration.toFixed(1)} Y` : "N/A"
  const convexity = bondDetails?.convexity?.toFixed(2) ?? "N/A"
  const dv01 = bondDetails?.dv01 ? `₹${bondDetails.dv01.toFixed(2)} per bp` : "N/A"
  const zSpread = bondDetails?.z_spread ? `+${bondDetails.z_spread} bps` : "N/A"
  const varValue = bondDetails?.var ? `₹${bondDetails.var.toFixed(2)}` : "N/A"
  const ytm = bondDetails?.ytm ? `${(bondDetails.ytm * 100).toFixed(2)}%` : "N/A"

  // Price forecast metrics from API
  const impliedVolatility = priceStats?.metrics.implied_volatility
    ? `${priceStats.metrics.implied_volatility.toFixed(2)}%`
    : "N/A"

  // ============================================================================
  // CHART DATA - Price Forecast with Percentile Bands
  // ============================================================================

  const chartData = React.useMemo(() => {
    if (!priceStats?.price_data || priceStats.price_data.length === 0) {
      return []
    }

    return priceStats.price_data.map((point) => ({
      date: point.date,
      displayDate: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      price: point.price,
      lower: point.price_5th_percentile,
      upper: point.price_95th_percentile,
    }))
  }, [priceStats])

  // Calculate additional metrics
  const currentYielding = ytm
  const volatility = impliedVolatility

  const oneMonthChange = React.useMemo(() => {
    if (!chartData || chartData.length < 2) return "N/A"
    const lastPoint = chartData[chartData.length - 1]
    const lastDate = new Date(lastPoint.date)
    const oneMonthAgo = new Date(lastDate)
    oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)
    
    const pastPoint = chartData.find(p => new Date(p.date) >= oneMonthAgo)
    
    if (pastPoint && lastPoint.price) {
      const change = ((lastPoint.price - pastPoint.price) / pastPoint.price) * 100
      return `${change > 0 ? "+" : ""}${change.toFixed(2)}%`
    }
    return "N/A"
  }, [chartData])

  const maxDrawdown = React.useMemo(() => {
    if (!chartData || chartData.length === 0) return "N/A"
    let maxPrice = -Infinity
    let maxDD = 0
    
    for (const point of chartData) {
      if (point.price > maxPrice) {
        maxPrice = point.price
      }
      const dd = (maxPrice - point.price) / maxPrice
      if (dd > maxDD) {
        maxDD = dd
      }
    }
    return `${(maxDD * 100).toFixed(2)}%`
  }, [chartData])

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold mb-2">{data.displayDate}</p>
          <p className="text-primary text-sm">
            Price: <span className="font-bold">₹{data.price?.toFixed(2)}</span>
          </p>
          <p className="text-white/70 text-xs mt-1">
            Range: ₹{data.lower?.toFixed(2)} - ₹{data.upper?.toFixed(2)}
          </p>
        </div>
      )
    }
    return null
  }

  // ============================================================================
  // CASH FLOW FILTERING
  // ============================================================================

  const getFilteredCashFlowData = () => {
    let filtered = [...ALL_CASH_FLOW_DATA]
    const today = new Date()

    // Update coupon percent based on bond data if available
    if (bondDetails?.coupon_rate) {
      const couponPercent = bondDetails.coupon_rate < 1 ? bondDetails.coupon_rate * 100 : bondDetails.coupon_rate
      filtered = filtered.map(row => ({ ...row, couponPercent }))
    }

    if (selectedTimeFilter === "Upcoming") {
      filtered = filtered.filter((row) => new Date(row.paymentDate) >= today)
    } else if (selectedTimeFilter === "Past") {
      filtered = filtered.filter((row) => new Date(row.paymentDate) < today)
    }

    if (selectedTypeFilter === "Coupon") {
      filtered = filtered.filter((row) => row.type === "Coupon")
    } else if (selectedTypeFilter === "Principal") {
      filtered = filtered.filter((row) => row.type.includes("Principal"))
    }

    if (dateRange) {
      const startDate = new Date(dateRange.start)
      const endDate = new Date(dateRange.end)
      filtered = filtered.filter((row) => {
        const paymentDate = new Date(row.paymentDate)
        return paymentDate >= startDate && paymentDate <= endDate
      })
    }

    return filtered
  }

  const filteredCashFlowData = getFilteredCashFlowData()

  // ============================================================================
  // RENDER
  // ============================================================================

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background text-white p-6">
        <BondHeaderSkeleton />
        <div className="grid grid-cols-3 gap-4 mb-6">
          <CouponCardSkeleton />
          <PriceCardSkeleton />
          <RiskMetricsSkeleton />
        </div>
        <div className="grid grid-cols-3 gap-4 mb-6">
          <ChartSkeleton />
          <div className="bg-card border border-border rounded-xl p-6">
            <SkeletonPulse className="h-5 w-36 mb-4" />
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-3">
                  <SkeletonPulse className="w-12 h-12 rounded" />
                  <div className="flex-1">
                    <SkeletonPulse className="h-4 w-full mb-2" />
                    <SkeletonPulse className="h-3 w-24" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (detailsError && isin) {
    return (
      <div className="min-h-screen bg-background text-white p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 text-lg mb-2">Failed to load bond details</p>
          <p className="text-white/70">Please try selecting a different bond or refresh the page.</p>
        </div>
      </div>
    )
  }

  // No bond selected state
  if (!isin && !selectedAsset) {
    return (
      <div className="min-h-screen bg-background text-white p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-white/70 text-lg mb-2">No bond selected</p>
          <p className="text-white/50">Select a bond from the Explore Assets page to view details.</p>
        </div>
      </div>
    )
  }

  // Handle adding more bonds from compare view
  const handleAddBondFromCompareView = () => {
    setShowCompareModal(true)
  }

  // Compare Modal JSX (inlined to prevent focus loss)
  const compareModalJSX = showCompareModal ? (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-xl font-semibold">Compare Bonds</h2>
          <button
            onClick={() => setShowCompareModal(false)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Selected Bonds */}
        <div className="p-4 border-b border-border">
          <p className="text-sm text-white/70 mb-2">Selected for comparison ({selectedBondsForCompare.length})</p>
          <div className="flex flex-wrap gap-2">
            {selectedBondsForCompare.map((bondIsin) => (
              <div
                key={bondIsin}
                className="flex items-center gap-2 px-3 py-1.5 bg-primary/20 text-primary rounded-full text-sm"
              >
                <span className="truncate max-w-[150px]">{bondIsin}</span>
                <button
                  onClick={() => toggleBondForCompare(bondIsin)}
                  className="hover:bg-primary/30 rounded-full p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
            {selectedBondsForCompare.length === 0 && (
              <p className="text-white/50 text-sm">No bonds selected</p>
            )}
          </div>
        </div>

        {/* Search Input */}
        <div className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
            <input
              type="text"
              placeholder="Search by ISIN or bond name..."
              value={compareSearchQuery}
              onChange={(e) => setCompareSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-background border border-border rounded-lg text-white placeholder:text-white/50 focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {/* Search Results */}
        <div className="px-4 pb-4 max-h-[300px] overflow-y-auto">
          {isSearching ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-background/50 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : searchResults?.results && searchResults.results.length > 0 ? (
            <div className="space-y-2">
              {searchResults.results.map((result) => {
                const isSelected = selectedBondsForCompare.includes(result.isin)
                return (
                  <div
                    key={result.isin}
                    onClick={() => toggleBondForCompare(result.isin)}
                    className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-primary/20 border border-primary"
                        : "bg-background/50 border border-transparent hover:bg-background hover:border-border"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{result.issuer} - {result.name}</p>
                      <p className="text-sm text-white/50">{result.isin}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-semibold">{result.current_yield_percent?.toFixed(2)}%</p>
                        <p className={`text-xs ${
                          result.yield_change_direction === 'up' ? 'text-green-400' :
                          result.yield_change_direction === 'down' ? 'text-red-400' :
                          'text-white/50'
                        }`}>
                          {result.yield_change_direction === 'up' ? '▲' : result.yield_change_direction === 'down' ? '▼' : '–'}
                          {' '}{Math.abs(result.yield_change * 100).toFixed(2)}%
                        </p>
                      </div>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                        isSelected ? "bg-primary text-black" : "border border-border"
                      }`}>
                        {isSelected && <Check className="w-4 h-4" />}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : compareSearchQuery.length >= 2 ? (
            <div className="text-center py-8 text-white/50">
              No bonds found matching "{compareSearchQuery}"
            </div>
          ) : (
            <div className="text-center py-8 text-white/50">
              Type at least 2 characters to search
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-border flex justify-end gap-3">
          <button
            onClick={() => setShowCompareModal(false)}
            className="px-6 py-2 text-white/70 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleOpenCompareView}
            disabled={selectedBondsForCompare.length < 2}
            className={`px-6 py-2 rounded-lg font-semibold transition-colors ${
              selectedBondsForCompare.length >= 2
                ? "bg-primary text-black hover:bg-primary/80"
                : "bg-gray-600 text-gray-400 cursor-not-allowed"
            }`}
          >
            Compare {selectedBondsForCompare.length >= 2 ? `(${selectedBondsForCompare.length})` : ""}
          </button>
        </div>
      </div>
    </div>
  ) : null

  // Show comparison view
  if (showCompareView) {
    return (
      <>
        {compareModalJSX}
        <BondCompare
          selectedIsins={selectedBondsForCompare}
          onBack={handleCloseCompareView}
          onRemoveBond={handleRemoveBondFromCompare}
          onAddBond={handleAddBondFromCompareView}
        />
      </>
    )
  }

  return (
    <div className="min-h-screen bg-background text-white p-6">
      {/* Compare Modal */}
      {compareModalJSX}

      {/* Trade Modal */}
      <TradeModal
        isOpen={tradeModalOpen}
        onClose={() => setTradeModalOpen(false)}
        tradeType={tradeType}
        ticker={bondIsin}
        assetName={bondName}
        currentPrice={lastPrice || 100}
        onExecute={handleExecuteTrade}
        isLoading={isTrading}
      />

      {/* Trade Success/Error Notification */}
      {tradeMessage && (
        <div
          className={`fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg ${
            tradeMessage.type === "success"
              ? "bg-green-500 text-white"
              : "bg-red-500 text-white"
          }`}
        >
          {tradeMessage.text}
        </div>
      )}

      {/* Title and Actions */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">{bondName}</h1>
          <p className="text-sm text-white/70">
            ISIN: {bondIsin} {bondDetails?.symbol && `/ Symbol: ${bondDetails.symbol}`}{" "}
            {creditRating !== "N/A" && <span className="text-primary">{creditRating}</span>}
          </p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => handleOpenTradeModal("buy")}
            className="px-8 py-3 bg-primary hover:bg-primary/80 text-black font-semibold rounded-lg"
          >
            Buy
          </button>
          <button 
            onClick={() => handleOpenTradeModal("sell")}
            className="px-8 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg"
          >
            Sell
          </button>
          <button 
            onClick={() => setShowCompareModal(true)}
            className="px-8 py-3 bg-transparent border-2 border-primary text-primary font-semibold rounded-lg flex items-center gap-2 hover:bg-primary/10 transition-colors"
          >
            Compare
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Top Info Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Coupon Info Card */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-white/70 text-sm mb-1">Coupon Rate</p>
              <p className="text-3xl font-bold">{couponRate}</p>
              <p className="text-white/70 text-sm">Semi - Annual</p>
            </div>
            <div>
              <p className="text-white/70 text-sm mb-1">Maturity Date</p>
              <p className="text-2xl font-bold">{maturityDate}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
            <div>
              <p className="text-white/70 text-sm mb-1">Next Coupon Date</p>
              <p className="text-xl font-bold">{nextCouponDate}</p>
            </div>
            <div>
              <p className="text-white/70 text-sm mb-1">Minimum Increment</p>
              <p className="text-xl font-bold">{minimumIncrement}</p>
              <p className="text-white/70 text-xs">Settlement Type: T+2</p>
            </div>
          </div>
        </div>

        {/* Price Info Card */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="mb-4">
            <div className="flex items-baseline justify-between mb-2">
              <p className="text-white/70 text-sm">Last Price</p>
              <div className="text-right">
                <p className="text-white/70 text-xs">Bid/Ask</p>
                <p className="text-sm">
                  {bidPrice.toFixed(2)} / {askPrice.toFixed(2)}
                </p>
              </div>
            </div>
            <div className="flex items-baseline gap-3">
              <p className="text-4xl font-bold">{lastPrice.toFixed(2)}</p>
              <p className="text-white/70 text-sm ml-auto">
                Bid - Ask
                <br />
                Spread
                <br />
                {spread.toFixed(2)}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
            <div>
              <p className="text-white/70 text-xs mb-1">Clean Price</p>
              <p className="text-lg font-bold">{cleanPrice.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-white/70 text-xs mb-1">Dirty Price</p>
              <p className="text-lg font-bold">{dirtyPrice.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-white/70 text-xs mb-1">Accrued Interest</p>
              <p className="text-lg font-bold">₹{accruedInterest.toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Risk Metrics Card */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">Risk Metrics</h3>
          <div className="grid grid-cols-3 gap-4 h-4/5">
            <div>
              <p className="text-white/70 text-xs mb-1">Duration</p>
              <p className="text-lg font-semibold">{duration}</p>
            </div>
            <div>
              <p className="text-white/70 text-xs mb-1">Convexity</p>
              <p className="text-lg font-semibold">{convexity}</p>
            </div>
            <div>
              <p className="text-white/70 text-xs mb-1">DV01</p>
              <p className="text-lg font-semibold">{dv01}</p>
            </div>
            <div>
              <p className="text-white/70 text-xs mb-1">YTM</p>
              <p className="text-lg font-semibold">{ytm}</p>
            </div>
            <div>
              <p className="text-white/70 text-xs mb-1">Z-Spread</p>
              <p className="text-lg font-semibold">{zSpread}</p>
            </div>
            <div>
              <p className="text-white/70 text-xs mb-1">VaR</p>
              <p className="text-lg font-semibold">{varValue}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Chart and News Section */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Chart Card */}
        <div className="col-span-2 bg-card border border-border rounded-xl p-6">
          {/* Time Period Selector */}
          <div className="flex gap-2 mb-4">
            {timePeriods.map((period) => (
              <button
                key={period}
                onClick={() => setSelectedTimePeriod(period)}
                className={`px-4 py-1 rounded text-sm transition-colors ${
                  selectedTimePeriod === period
                    ? "bg-primary/20 text-primary border border-primary"
                    : "text-white/70 hover:text-primary hover:bg-primary/10"
                }`}
              >
                {period}
              </button>
            ))}
          </div>

          {isLoadingPrice ? (
            <ChartSkeleton />
          ) : (
            <>
              <div className="h-64 mb-4 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis 
                      dataKey="displayDate" 
                      stroke="#94a3b8" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false}
                      minTickGap={30}
                    />
                    <YAxis 
                      stroke="#94a3b8" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false}
                      domain={['auto', 'auto']}
                      tickFormatter={(value) => `₹${value}`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="lower"
                      stroke="none"
                      fill="#1e293b"
                      fillOpacity={0.3}
                    />
                    <Area
                      type="monotone"
                      dataKey="upper"
                      stroke="none"
                      fill="#1e293b"
                      fillOpacity={0.3}
                    />
                    <Line
                      type="monotone"
                      dataKey="price"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 6, fill: "#06b6d4" }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div>
                  <p className="text-white/70 text-xs mb-1">Current Yielding</p>
                  <p className="text-xl font-bold text-primary">{currentYielding}</p>
                </div>
                <div>
                  <p className="text-white/70 text-xs mb-1">1-Month Change</p>
                  <p className="text-xl font-bold text-primary">{oneMonthChange}</p>
                </div>
                <div>
                  <p className="text-white/70 text-xs mb-1">Volatility (20 D σ)</p>
                  <p className="text-xl font-bold">{volatility}</p>
                </div>
                <div>
                  <p className="text-white/70 text-xs mb-1">Max Drawdown (1 Y)</p>
                  <p className="text-xl font-bold text-primary">{maxDrawdown}</p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* News Card */}
        <div className="bg-card border border-border rounded-xl p-6 flex flex-col h-[400px]">
          <h3 className="text-lg font-semibold mb-4 flex-shrink-0">News and analytics</h3>
          <div className="space-y-4 overflow-y-auto flex-1 pr-2 custom-scrollbar">
            {isLoadingNews ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex gap-3">
                    <SkeletonPulse className="w-12 h-12 rounded flex-shrink-0" />
                    <div className="flex-1">
                      <SkeletonPulse className="h-4 w-full mb-2" />
                      <SkeletonPulse className="h-3 w-24" />
                    </div>
                  </div>
                ))}
              </div>
            ) : newsArticles && newsArticles.length > 0 ? (
              newsArticles.map((article) => (
                <div key={article.article_id} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700 hover:border-primary/50 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <a 
                      href={article.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-sm font-medium hover:text-primary flex items-center gap-1 flex-1 mr-2"
                    >
                      {article.title}
                      <ExternalLink className="w-3 h-3 flex-shrink-0" />
                    </a>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase font-bold flex-shrink-0 ${
                      article.sentiment_label === 'positive' ? 'bg-green-500/20 text-green-400' :
                      article.sentiment_label === 'negative' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {article.sentiment_label}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-2 text-[10px] text-white/50 mb-2">
                    <span>{article.source}</span>
                    <span>•</span>
                    <span>{new Date(article.published_at).toLocaleDateString()}</span>
                    {article.liquidity_impact && (
                      <>
                        <span>•</span>
                        <span className={
                          article.liquidity_impact.includes('POSITIVE') ? 'text-green-400' :
                          article.liquidity_impact.includes('NEGATIVE') ? 'text-red-400' :
                          'text-yellow-400'
                        }>
                          {article.liquidity_impact.replace('_', ' ')}
                        </span>
                      </>
                    )}
                  </div>

                  <p className="text-xs text-white/70 line-clamp-3 mb-2">
                    {article.summary}
                  </p>

                  {article.impact_assessment && (
                    <div className="mt-2 pt-2 border-t border-gray-700">
                      <p className="text-[10px] text-white/50 uppercase mb-1">Impact Assessment</p>
                      <p className="text-xs text-white/80 italic">
                        "{article.impact_assessment}"
                      </p>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-white/50">
                No news available for this bond
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Portfolio Impact and Summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Impact on Portfolio */}
        <div className="col-span-2 bg-card border border-border rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">Impact on Portfolio</h3>
          <div className="flex justify-between items-center">
            <div>
              <p className="text-white/70 text-sm mb-1">Allocation</p>
              <p className="text-2xl font-bold">{PORTFOLIO_IMPACT.allocation}</p>
            </div>
            <div>
              <p className="text-white/70 text-sm mb-1">Portfolio YieldΔ</p>
              <p className="text-2xl font-bold text-primary">{PORTFOLIO_IMPACT.portfolioYieldDelta}</p>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3">Summary</h3>
          <p className="text-xs text-white/70 leading-relaxed">{SUMMARY_TEXT}</p>
        </div>
      </div>

      {/* Cash Flow Schedule */}
      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Coupon & Cash Flow Schedule</h3>

        <div className="flex gap-2 mb-4 flex-wrap">
          {/* Time filters */}
          {["All", "Upcoming", "Past"].map((filter) => (
            <button
              key={filter}
              onClick={() => setSelectedTimeFilter(filter)}
              className={`px-4 py-2 rounded text-sm transition-colors ${
                selectedTimeFilter === filter
                  ? "bg-primary text-black font-semibold"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {filter}
            </button>
          ))}

          {/* Type filters */}
          {["All Types", "Coupon", "Principal"].map((filter) => (
            <button
              key={filter}
              onClick={() => setSelectedTypeFilter(filter)}
              className={`px-4 py-2 rounded text-sm transition-colors ${
                selectedTypeFilter === filter
                  ? "bg-primary text-black font-semibold"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {filter}
            </button>
          ))}

          <div className="ml-auto relative">
            <button
              onClick={() => setShowDatePicker(!showDatePicker)}
              className="px-4 py-2 rounded text-sm bg-gray-700 text-gray-300 flex items-center gap-2 hover:bg-gray-600"
            >
              <Calendar className="w-4 h-4" />
              Date Range
              {dateRange && <span className="text-primary">✓</span>}
            </button>

            {showDatePicker && (
              <div className="absolute right-0 top-12 bg-card border border-border rounded-lg p-4 z-10 min-w-[300px]">
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-white/70 block mb-1">Start Date</label>
                    <input
                      type="date"
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white"
                      value={dateRange?.start || ""}
                      onChange={(e) => setDateRange({ start: e.target.value, end: dateRange?.end || e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-white/70 block mb-1">End Date</label>
                    <input
                      type="date"
                      className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white"
                      value={dateRange?.end || ""}
                      onChange={(e) => setDateRange({ start: dateRange?.start || e.target.value, end: e.target.value })}
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setDateRange(null)
                        setShowDatePicker(false)
                      }}
                      className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
                    >
                      Clear
                    </button>
                    <button
                      onClick={() => setShowDatePicker(false)}
                      className="flex-1 px-3 py-2 bg-primary hover:bg-primary/80 text-black rounded text-sm font-semibold"
                    >
                      Apply
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-sm font-semibold text-white/70">Payment Date</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-white/70">Type</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-white/70">Coupon %</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-white/70">Days</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-white/70">Principal</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-white/70">Total Payment</th>
              </tr>
            </thead>
            <tbody>
              {filteredCashFlowData.length > 0 ? (
                filteredCashFlowData.map((row, index) => (
                  <tr key={index} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                    <td className="py-3 px-4 text-sm">{row.paymentDate}</td>
                    <td className="py-3 px-4 text-sm">{row.type}</td>
                    <td className="py-3 px-4 text-sm">{row.couponPercent.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm">{row.days}</td>
                    <td className="py-3 px-4 text-sm">{row.principal}</td>
                    <td className="py-3 px-4 text-sm font-semibold">{row.totalPayment}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-white/70">
                    No payments match the selected filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Floating Chat */}
      <BondChat bondName={bondName} bondIsin={bondIsin} />
    </div>
  )
}
