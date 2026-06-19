"use client"

import React, { useState, useMemo, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, ReferenceLine 
} from "recharts"
import { TrendingUp, TrendingDown, Info, Loader2, ArrowUpRight, ArrowDownRight, Minus, History, X, MessageCircle, Send } from "lucide-react"
import { 
  useForexPairs, 
  useRecommendedTrades, 
  useCurrencyPriceData, 
  useRiskMetrics, 
  usePortfolioExposure,
  useExecuteTrade,
  usePortfolioSummary,
  useCumulativeProfit,
  useProfitChartData,
  useTradeRecords
} from "@/queries/forex_queries"
import { executeTrade as executePortfolioTrade, type TradeRequest } from "@/api/portfolio"
import ReactMarkdown from "react-markdown"

// ============================================================================
// TRADE MODAL COMPONENT
// ============================================================================

interface ForexTradeModalProps {
  isOpen: boolean
  onClose: () => void
  tradeType: "buy" | "sell"
  pair: string
  currentPrice: number
  onExecute: (amount: number) => Promise<void>
  isLoading: boolean
}

function ForexTradeModal({
  isOpen,
  onClose,
  tradeType,
  pair,
  currentPrice,
  onExecute,
  isLoading,
}: ForexTradeModalProps) {
  const [amount, setAmount] = useState<string>("10000")
  const [error, setError] = useState<string>("")

  const handleSubmit = async () => {
    const amt = parseFloat(amount)
    if (isNaN(amt) || amt <= 0) {
      setError("Please enter a valid amount")
      return
    }
    setError("")
    await onExecute(amt)
    setAmount("10000")
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div 
        className="rounded-xl w-full max-w-md animate-in fade-in zoom-in duration-200"
        style={{ backgroundColor: "#0d1f2d", border: "1px solid #145b5b" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4" style={{ borderBottom: "1px solid #145b5b" }}>
          <h2 className={`text-xl font-semibold ${tradeType === "buy" ? "text-green-500" : "text-red-500"}`}>
            {tradeType === "buy" ? "Buy" : "Sell"} {pair}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Pair Info */}
          <div className="rounded-lg p-3" style={{ backgroundColor: "#0b1623" }}>
            <p className="text-sm text-gray-400">Currency Pair</p>
            <p className="font-semibold text-white">{pair}</p>
          </div>

          {/* Current Rate */}
          <div className="rounded-lg p-3" style={{ backgroundColor: "#0b1623" }}>
            <p className="text-sm text-gray-400">Current Rate</p>
            <p className="font-semibold text-lg text-white">{currentPrice.toFixed(5)}</p>
          </div>

          {/* Amount Input */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Amount (USD)</label>
            <input
              type="number"
              min="100"
              step="100"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full rounded-lg px-4 py-3 text-white focus:outline-none"
              style={{ backgroundColor: "#0b1623", border: "1px solid #145b5b" }}
              placeholder="Enter amount"
            />
            {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
          </div>

          {/* Estimated Value */}
          <div className="rounded-lg p-3" style={{ backgroundColor: "#0b1623" }}>
            <p className="text-sm text-gray-400">Position Value</p>
            <p className="font-bold text-xl text-white">
              ${parseFloat(amount || "0").toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 flex gap-3" style={{ borderTop: "1px solid #145b5b" }}>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
            style={{ border: "1px solid #145b5b", color: "#94a3b8" }}
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

// Colors
const C = {
  teal: "#14b8a6",
  tealLight: "#2dd4bf",
  tealDark: "#0d9488",
  red: "#ef4444",
  redLight: "#f87171",
  green: "#22c55e",
  greenLight: "#4ade80",
  amber: "#f59e0b",
  blue: "#3b82f6",
  white: "#ffffff",
  textPrimary: "#f1f5f9",
  textSecondary: "#94a3b8",
  textMuted: "#64748b",
  bgDark: "#0b1623",
  bgCard: "#0d1f2d",
  border: "#145b5b",
}

const CURRENCY_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "EURINR", "GBPINR", "JPYINR"]

type TimePeriod = "1D" | "1W" | "1M" | "3M" | "1Y"

const periodToDays: Record<TimePeriod, number> = {
  "1D": 1,
  "1W": 7,
  "1M": 30,
  "3M": 90,
  "1Y": 365,
}

// Format currency
const formatPrice = (value: number, decimals: number = 5) => {
  return value?.toFixed(decimals) ?? "0.00000"
}

const formatCurrency = (value: number) => {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(2)}K`
  return `$${value.toFixed(2)}`
}

const formatPercent = (value: number) => {
  const sign = value >= 0 ? "+" : ""
  return `${sign}${value.toFixed(2)}%`
}

export function FXTradingDashboard() {
  const [selectedPair, setSelectedPair] = useState<string>("EURUSD")
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>("1M")
  
  // Trade modal state
  const [tradeModalOpen, setTradeModalOpen] = useState(false)
  const [tradeType, setTradeType] = useState<"buy" | "sell">("buy")
  const [isTrading, setIsTrading] = useState(false)
  const [tradeMessage, setTradeMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  
  // Chat state
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([])
  const [chatInput, setChatInput] = useState("")
  const [isChatLoading, setIsChatLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Queries
  const { data: pairsData, isLoading: pairsLoading } = useForexPairs()
  const { data: recommendedTrades } = useRecommendedTrades()
  const { data: priceData, isLoading: priceLoading } = useCurrencyPriceData(selectedPair, periodToDays[selectedPeriod])
  const { data: riskMetrics } = useRiskMetrics(selectedPair)
  const { data: exposure, refetch: refetchExposure } = usePortfolioExposure(selectedPair)
  const { data: portfolio, refetch: refetchPortfolio } = usePortfolioSummary()
  const { data: profitData, refetch: refetchProfit } = useCumulativeProfit(selectedPair)
  const { data: profitChartData, refetch: refetchProfitChart } = useProfitChartData(selectedPair)
  const { data: tradeRecords, refetch: refetchTradeRecords } = useTradeRecords(selectedPair, 50)

  const executeTrade = useExecuteTrade()

  // Get current pair info
  const currentPairInfo = useMemo(() => {
    return pairsData?.pairs?.find(p => p.pair === selectedPair)
  }, [pairsData, selectedPair])

  const currentRecommendation = useMemo(() => {
    return recommendedTrades?.trades?.find(t => t.pair === selectedPair)
  }, [recommendedTrades, selectedPair])

  // Transform price data for charts
  const chartData = useMemo(() => {
    if (!priceData?.data) return []
    return priceData.data.map((d, idx) => ({
      time: new Date(d.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      close: d.close,
      high: d.high,
      low: d.low,
      open: d.open,
      index: idx,
    }))
  }, [priceData])

  const profitCurveData = useMemo(() => {
    if (!profitChartData?.data_points) return []
    return profitChartData.data_points.map((d: any, idx: number) => ({
      date: d.date,
      pnl: d.cumulative_pnl_pct,
      tradePnl: d.trade_pnl_pct,
      capital: d.capital,
      index: idx,
    }))
  }, [profitChartData])

  // Sort trade records - open trades first, then by date
  const sortedTradeRecords = useMemo(() => {
    if (!tradeRecords?.records) return []
    return [...tradeRecords.records].sort((a, b) => {
      // Open trades come first
      if (a.status === 'open' && b.status !== 'open') return -1
      if (a.status !== 'open' && b.status === 'open') return 1
      // Then sort by date (newest first)
      const dateA = new Date(a.entry_datetime || 0).getTime()
      const dateB = new Date(b.entry_datetime || 0).getTime()
      return dateB - dateA
    })
  }, [tradeRecords])

  // Open trade modal
  const handleOpenTradeModal = (type: "buy" | "sell") => {
    setTradeType(type)
    setTradeModalOpen(true)
    setTradeMessage(null)
  }

  // Handle trade execution with quantity modal
  const handleExecuteTradeWithAmount = async (amount: number) => {
    setIsTrading(true)
    try {
      // Execute on forex API
      executeTrade.mutate(
        { pair: selectedPair, action: tradeType, amount },
        {
          onSuccess: async () => {
            // Also track in portfolio API
            try {
              const portfolioRequest: TradeRequest = {
                asset_type: "forex",
                ticker: selectedPair,
                action: tradeType,
                quantity: amount,
                price: currentPairInfo?.current_price || 1,
                asset_name: selectedPair,
              }
              await executePortfolioTrade(portfolioRequest)
            } catch (e) {
              console.error("Failed to track in portfolio:", e)
            }
            
            // Immediately refetch position-related data
            refetchExposure()
            refetchPortfolio()
            refetchProfit()
            refetchProfitChart()
            refetchTradeRecords()
            
            setTradeMessage({ type: "success", text: `Successfully ${tradeType === "buy" ? "bought" : "sold"} ${amount} ${selectedPair}` })
            setTradeModalOpen(false)
            setTimeout(() => setTradeMessage(null), 3000)
          },
          onError: (error: any) => {
            setTradeMessage({ type: "error", text: error.message || "Trade failed" })
          }
        }
      )
    } finally {
      setIsTrading(false)
    }
  }

  // Handle close position (hold)
  const handleClosePosition = async () => {
    executeTrade.mutate(
      { pair: selectedPair, action: 'hold', amount: 0 },
      {
        onSuccess: () => {
          refetchExposure()
          refetchPortfolio()
          refetchProfit()
          refetchProfitChart()
          refetchTradeRecords()
        }
      }
    )
  }

  // Chat handlers
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handleChatSend = async () => {
    if (!chatInput.trim() || isChatLoading) return

    const userMessage = chatInput.trim()
    setChatInput("")
    
    const newUserMessage = { role: 'user' as const, content: userMessage }
    setChatMessages(prev => [...prev, newUserMessage])
    setIsChatLoading(true)

    try {
      const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/forex/v1/agent/query`
      const response = await fetch(API_BASE, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage,
          pairs: [selectedPair],
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      const assistantMessage = { 
        role: 'assistant' as const, 
        content: data.response || 'No response from agent.' 
      }
      setChatMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = { 
        role: 'assistant' as const, 
        content: 'Sorry, there was an error processing your request.' 
      }
      setChatMessages(prev => [...prev, errorMessage])
    } finally {
      setIsChatLoading(false)
    }
  }

  const handleChatKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleChatSend()
    }
  }

  const isLoading = pairsLoading || priceLoading

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: C.bgDark }}>
        <Loader2 className="h-8 w-8 animate-spin" style={{ color: C.teal }} />
      </div>
    )
  }

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: C.bgDark, color: C.textPrimary }}>
      {/* Trade Modal */}
      <ForexTradeModal
        isOpen={tradeModalOpen}
        onClose={() => setTradeModalOpen(false)}
        tradeType={tradeType}
        pair={selectedPair}
        currentPrice={currentPairInfo?.current_price || 1}
        onExecute={handleExecuteTradeWithAmount}
        isLoading={isTrading || executeTrade.isPending}
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

      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Select value={selectedPair} onValueChange={setSelectedPair}>
            <SelectTrigger 
              className="w-48 text-xl font-bold"
              style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}`, color: C.textPrimary }}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              {CURRENCY_PAIRS.map(pair => (
                <SelectItem key={pair} value={pair} style={{ color: C.textPrimary }}>
                  {pair}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {currentPairInfo && (
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold" style={{ color: C.textPrimary }}>
                {formatPrice(currentPairInfo.current_price)}
              </span>
              <span 
                className="text-sm font-medium flex items-center gap-1"
                style={{ color: currentPairInfo.price_change_pct_1d >= 0 ? C.green : C.red }}
              >
                {currentPairInfo.price_change_pct_1d >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                {formatPercent(currentPairInfo.price_change_pct_1d)}
              </span>
            </div>
          )}
        </div>
        
        <div className="flex gap-2">
          <Button 
            onClick={() => handleOpenTradeModal('buy')}
            disabled={executeTrade.isPending}
            className="transition-all duration-300 hover:scale-105"
            style={{ backgroundColor: C.teal, color: C.white }}
          >
            {executeTrade.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Buy'}
          </Button>
          <Button 
            onClick={() => handleOpenTradeModal('sell')}
            disabled={executeTrade.isPending}
            className="transition-all duration-300 hover:scale-105"
            style={{ backgroundColor: C.red, color: C.white }}
          >
            {executeTrade.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sell'}
          </Button>
          <Button 
            onClick={handleClosePosition}
            disabled={executeTrade.isPending}
            variant="outline"
            className="transition-all duration-300 hover:scale-105"
            style={{ borderColor: C.border, color: C.textSecondary, backgroundColor: 'transparent' }}
          >
            Close Position
          </Button>
        </div>
      </div>

      {/* Current Position Card - Prominent Display */}
      <Card 
        className="mb-6"
        style={{ 
          backgroundColor: C.bgCard, 
          border: `1px solid ${
            exposure?.current_position === 'long' ? C.green : 
            exposure?.current_position === 'short' ? C.red : 
            C.border
          }`,
        }}
      >
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            {/* Position Status */}
            <div className="flex items-center gap-4">
              <div 
                className="p-3 rounded-lg"
                style={{ 
                  backgroundColor: exposure?.current_position === 'long' ? `${C.green}20` : 
                                   exposure?.current_position === 'short' ? `${C.red}20` : 
                                   `${C.textMuted}15` 
                }}
              >
                {exposure?.current_position === 'long' ? (
                  <ArrowUpRight className="w-8 h-8" style={{ color: C.green }} />
                ) : exposure?.current_position === 'short' ? (
                  <ArrowDownRight className="w-8 h-8" style={{ color: C.red }} />
                ) : (
                  <Minus className="w-8 h-8" style={{ color: C.textMuted }} />
                )}
              </div>
              <div>
                <p className="text-xs uppercase tracking-wider" style={{ color: C.textMuted }}>
                  Current Position
                </p>
                <p 
                  className="text-2xl font-bold uppercase"
                  style={{ 
                    color: exposure?.current_position === 'long' ? C.green : 
                           exposure?.current_position === 'short' ? C.red : 
                           C.textSecondary 
                  }}
                >
                  {exposure?.current_position || 'No Position'}
                </p>
                <p className="text-sm" style={{ color: C.textSecondary }}>
                  {selectedPair}
                </p>
              </div>
            </div>

            {/* Position Details */}
            {exposure?.current_position !== 'flat' && (exposure?.position_size ?? 0) > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Position Size</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {formatCurrency(exposure?.position_size || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Entry Price</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {exposure?.avg_buy_price ? formatPrice(exposure.avg_buy_price) : 
                     exposure?.avg_sell_price ? formatPrice(exposure.avg_sell_price) : 
                     '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Current Price</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {formatPrice(currentPairInfo?.current_price || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Unrealized P&L</p>
                  <p 
                    className="text-lg font-semibold"
                    style={{ color: (exposure?.unrealized_pnl_pct || 0) >= 0 ? C.green : C.red }}
                  >
                    {formatPercent(exposure?.unrealized_pnl_pct || 0)}
                  </p>
                  <p 
                    className="text-xs"
                    style={{ color: (exposure?.unrealized_pnl || 0) >= 0 ? C.green : C.red }}
                  >
                    {formatCurrency(exposure?.unrealized_pnl || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Days Held</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {exposure?.days_held || 0}
                  </p>
                  <p className="text-xs" style={{ color: C.textMuted }}>
                    {exposure?.entry_date || '-'}
                  </p>
                </div>
              </div>
            ) : (
              <div 
                className="flex items-center gap-2 px-4 py-2 rounded-lg"
                style={{ backgroundColor: `${C.textMuted}15` }}
              >
                <Info className="w-4 h-4" style={{ color: C.textMuted }} />
                <p className="text-sm" style={{ color: C.textMuted }}>
                  No active position for {selectedPair}. Use Buy or Sell to open a position.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Charts */}
        <div className="lg:col-span-2 space-y-6">
          {/* Price Chart */}
          <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle style={{ color: C.textPrimary }}>Price Chart</CardTitle>
                <div className="flex gap-1">
                  {(["1D", "1W", "1M", "3M", "1Y"] as TimePeriod[]).map((period) => (
                    <button
                      key={period}
                      onClick={() => setSelectedPeriod(period)}
                      className="px-3 py-1 text-xs rounded transition-all duration-300"
                      style={{
                        backgroundColor: selectedPeriod === period ? C.teal : `${C.teal}20`,
                        color: selectedPeriod === period ? C.white : C.textSecondary,
                      }}
                    >
                      {period}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={C.teal} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={C.teal} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} opacity={0.3} />
                  <XAxis 
                    dataKey="time" 
                    stroke={C.textMuted} 
                    tick={{ fill: C.textSecondary, fontSize: 11 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis 
                    stroke={C.textMuted} 
                    tick={{ fill: C.textSecondary, fontSize: 11 }}
                    domain={['auto', 'auto']}
                    tickFormatter={(v) => v.toFixed(4)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: C.bgCard,
                      border: `1px solid ${C.border}`,
                      borderRadius: 8,
                      color: C.textPrimary,
                    }}
                    labelStyle={{ color: C.teal }}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke={C.teal}
                    strokeWidth={2}
                    fill="url(#priceGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
              
              {/* Metrics Below Chart */}
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4" style={{ borderTop: `1px solid ${C.border}` }}>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Spot Rate</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {formatPrice(priceData?.spot_rate || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>10D Volatility</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {((priceData?.realized_volatility_10d || 0) * 100).toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>20D Volatility</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {((priceData?.realized_volatility_20d || 0) * 100).toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>ATR (14D)</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {formatPrice(priceData?.atr_14d || 0)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Profit Curve Chart */}
          <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle style={{ color: C.textPrimary }}>Profit Curve - {selectedPair}</CardTitle>
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: C.textMuted }}>
                    Total Return:
                  </span>
                  <span 
                    className="text-sm font-semibold"
                    style={{ color: (profitChartData?.total_return_pct || 0) >= 0 ? C.green : C.red }}
                  >
                    {formatPercent(profitChartData?.total_return_pct || 0)}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {profitCurveData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={profitCurveData}>
                    <defs>
                      <linearGradient id="profitGradientPositive" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={C.green} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={C.green} stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="profitGradientNegative" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={C.red} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={C.red} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={C.border} opacity={0.3} />
                    <XAxis 
                      dataKey="date" 
                      stroke={C.textMuted} 
                      tick={{ fill: C.textSecondary, fontSize: 11 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis 
                      stroke={C.textMuted} 
                      tick={{ fill: C.textSecondary, fontSize: 11 }}
                      tickFormatter={(v) => `${v.toFixed(1)}%`}
                      domain={['auto', 'auto']}
                    />
                    <ReferenceLine y={0} stroke={C.textMuted} strokeDasharray="3 3" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: C.bgCard,
                        border: `1px solid ${C.border}`,
                        borderRadius: 8,
                        color: C.textPrimary,
                      }}
                      labelStyle={{ color: C.teal }}
                      formatter={(value: number, name: string) => {
                        if (name === 'pnl') return [`${value.toFixed(2)}%`, 'Cumulative P&L']
                        if (name === 'tradePnl') return [`${value.toFixed(2)}%`, 'Trade P&L']
                        return [value, name]
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="pnl"
                      stroke={(profitChartData?.total_return_pct || 0) >= 0 ? C.green : C.red}
                      strokeWidth={2}
                      fill={(profitChartData?.total_return_pct || 0) >= 0 ? "url(#profitGradientPositive)" : "url(#profitGradientNegative)"}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div 
                  className="h-[250px] flex flex-col items-center justify-center"
                  style={{ color: C.textMuted }}
                >
                  <p>No profit history available</p>
                  <p className="text-xs mt-1">Execute some trades to see your profit curve</p>
                </div>
              )}
              
              {/* Capital summary below chart */}
              {profitCurveData.length > 0 && (
                <div 
                  className="grid grid-cols-3 gap-4 mt-4 pt-4" 
                  style={{ borderTop: `1px solid ${C.border}` }}
                >
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Starting Capital</p>
                    <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                      {formatCurrency(profitChartData?.starting_capital || 100000)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Current Capital</p>
                    <p 
                      className="text-lg font-semibold"
                      style={{ color: (profitChartData?.final_capital || 0) >= (profitChartData?.starting_capital || 100000) ? C.green : C.red }}
                    >
                      {formatCurrency(profitChartData?.final_capital || 100000)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Total Trades</p>
                    <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                      {profitChartData?.total_data_points || 0}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Risk Tracking & Exposure Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Risk Tracking */}
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ color: C.textPrimary }}>Risk Tracking</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { label: "Volatility (10D)", value: `${((riskMetrics?.volatility_10d || 0) * 100).toFixed(2)}%` },
                  { label: "Volatility (20D)", value: `${((riskMetrics?.volatility_20d || 0) * 100).toFixed(2)}%` },
                  { label: "VaR (95%)", value: `${(riskMetrics?.value_at_risk_95 || 0).toFixed(2)}%` },
                  { label: "VaR (99%)", value: `${(riskMetrics?.value_at_risk_99 || 0).toFixed(2)}%` },
                  { label: "Sharpe Ratio", value: (riskMetrics?.strategy_sharpe || 0).toFixed(2) },
                  { label: "Max Drawdown", value: `${(riskMetrics?.max_drawdown_pct || 0).toFixed(2)}%` },
                  { label: "Position Size", value: formatCurrency(riskMetrics?.position_size || 0) },
                ].map((item, idx) => (
                  <div 
                    key={idx} 
                    className="flex justify-between items-center p-2 rounded transition-colors cursor-pointer"
                    style={{ backgroundColor: `${C.teal}05` }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = `${C.teal}15`}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = `${C.teal}05`}
                  >
                    <span className="text-xs" style={{ color: C.textMuted }}>{item.label}</span>
                    <span className="text-sm font-semibold" style={{ color: C.textPrimary }}>{item.value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Portfolio Exposure */}
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ color: C.textPrimary }}>Portfolio Exposure</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <p className="text-xs" style={{ color: C.textMuted }}>Position</p>
                  <p 
                    className="text-2xl font-bold capitalize"
                    style={{ 
                      color: exposure?.current_position === 'long' ? C.green : 
                             exposure?.current_position === 'short' ? C.red : 
                             C.textSecondary 
                    }}
                  >
                    {exposure?.current_position || 'Flat'}
                  </p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Unrealized P&L</p>
                    <p 
                      className="text-lg font-semibold"
                      style={{ color: (exposure?.unrealized_pnl_pct || 0) >= 0 ? C.green : C.red }}
                    >
                      {formatPercent(exposure?.unrealized_pnl_pct || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Realized P&L</p>
                    <p 
                      className="text-lg font-semibold"
                      style={{ color: (exposure?.realized_pnl || 0) >= 0 ? C.green : C.red }}
                    >
                      {formatPercent(exposure?.realized_pnl || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Position Size</p>
                    <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                      {formatCurrency(exposure?.position_size || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Portfolio %</p>
                    <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                      {(exposure?.portfolio_exposure_pct || 0).toFixed(1)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Days Held</p>
                    <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                      {exposure?.days_held || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs" style={{ color: C.textMuted }}>Entry Date</p>
                    <p className="text-sm font-semibold" style={{ color: C.textPrimary }}>
                      {exposure?.entry_date || '-'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Right Column - Info Cards */}
        <div className="space-y-6">
          {/* Recommendation */}
          {currentRecommendation && (
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ color: C.textPrimary }}>AI Recommendation</CardTitle>
              </CardHeader>
              <CardContent>
                <div 
                  className="p-4 rounded-lg mb-4"
                  style={{ 
                    backgroundColor: currentRecommendation.action === 'buy' ? `${C.green}15` :
                                     currentRecommendation.action === 'sell' ? `${C.red}15` :
                                     `${C.textMuted}15`,
                    border: `1px solid ${currentRecommendation.action === 'buy' ? C.green :
                                         currentRecommendation.action === 'sell' ? C.red :
                                         C.textMuted}50`
                  }}
                >
                  <p 
                    className="text-2xl font-bold uppercase mb-1"
                    style={{ 
                      color: currentRecommendation.action === 'buy' ? C.green :
                             currentRecommendation.action === 'sell' ? C.red :
                             C.textSecondary
                    }}
                  >
                    {currentRecommendation.action}
                  </p>
                  <p className="text-sm" style={{ color: C.textMuted }}>
                    Signal Strength: <span style={{ color: C.textPrimary }}>{currentRecommendation.signal_strength}</span>
                  </p>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-xs" style={{ color: C.textMuted }}>Model Confidence</span>
                    <span className="text-sm font-medium" style={{ color: C.textPrimary }}>
                      {(currentRecommendation.model_confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs" style={{ color: C.textMuted }}>Predicted Return</span>
                    <span 
                      className="text-sm font-medium"
                      style={{ color: currentRecommendation.predicted_return >= 0 ? C.green : C.red }}
                    >
                      {formatPercent(currentRecommendation.predicted_return * 100)}
                    </span>
                  </div>
                  {currentRecommendation.stop_loss && (
                    <div className="flex justify-between">
                      <span className="text-xs" style={{ color: C.textMuted }}>Stop Loss</span>
                      <span className="text-sm font-medium" style={{ color: C.red }}>
                        {formatPrice(currentRecommendation.stop_loss)}
                      </span>
                    </div>
                  )}
                  {currentRecommendation.take_profit && (
                    <div className="flex justify-between">
                      <span className="text-xs" style={{ color: C.textMuted }}>Take Profit</span>
                      <span className="text-sm font-medium" style={{ color: C.green }}>
                        {formatPrice(currentRecommendation.take_profit)}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Cumulative Profit */}
          <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
            <CardHeader className="pb-2">
              <CardTitle style={{ color: C.textPrimary }}>Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <p className="text-xs" style={{ color: C.textMuted }}>Total Profit</p>
                <p 
                  className="text-2xl font-bold"
                  style={{ color: (profitData?.total_profit_pct || 0) >= 0 ? C.green : C.red }}
                >
                  {formatPercent(profitData?.total_profit_pct || 0)}
                </p>
                <p className="text-sm" style={{ color: C.textSecondary }}>
                  {formatCurrency(profitData?.total_profit_amount || 0)}
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Total Trades</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {profitData?.total_trades || 0}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Win Rate</p>
                  <p className="text-lg font-semibold" style={{ color: C.textPrimary }}>
                    {((profitData?.win_rate || 0) * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Best Trade</p>
                  <p className="text-lg font-semibold" style={{ color: C.green }}>
                    {formatPercent(profitData?.largest_win_pct || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: C.textMuted }}>Worst Trade</p>
                  <p className="text-lg font-semibold" style={{ color: C.red }}>
                    {formatPercent(profitData?.largest_loss_pct || 0)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Portfolio Summary */}
          {portfolio && (
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ color: C.textPrimary }}>Portfolio Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-xs" style={{ color: C.textMuted }}>Open Positions</span>
                  <span className="text-sm font-medium" style={{ color: C.textPrimary }}>
                    {portfolio.total_open_positions}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs" style={{ color: C.textMuted }}>Long Exposure</span>
                  <span className="text-sm font-medium" style={{ color: C.green }}>
                    {formatCurrency(portfolio.total_exposure_long)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs" style={{ color: C.textMuted }}>Short Exposure</span>
                  <span className="text-sm font-medium" style={{ color: C.red }}>
                    {formatCurrency(portfolio.total_exposure_short)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs" style={{ color: C.textMuted }}>Net Exposure</span>
                  <span 
                    className="text-sm font-medium"
                    style={{ color: portfolio.net_exposure >= 0 ? C.green : C.red }}
                  >
                    {formatCurrency(portfolio.net_exposure)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs" style={{ color: C.textMuted }}>Unrealized P&L</span>
                  <span 
                    className="text-sm font-medium"
                    style={{ color: portfolio.total_unrealized_pnl_pct >= 0 ? C.green : C.red }}
                  >
                    {formatPercent(portfolio.total_unrealized_pnl_pct)}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Trade History Table */}
       <Card className="mt-6" style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5" style={{ color: C.teal }} />
              <CardTitle style={{ color: C.textPrimary }}>Trade History - {selectedPair}</CardTitle>
            </div>
            <span className="text-xs" style={{ color: C.textMuted }}>
              {tradeRecords?.total_count || tradeRecords?.records?.length || 0} trades
            </span>
          </div>
        </CardHeader>
        <CardContent>
          {sortedTradeRecords.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    <th className="text-left py-3 px-2 text-xs font-medium" style={{ color: C.textMuted }}>Date</th>
                    <th className="text-left py-3 px-2 text-xs font-medium" style={{ color: C.textMuted }}>Pair</th>
                    <th className="text-left py-3 px-2 text-xs font-medium" style={{ color: C.textMuted }}>Side</th>
                    <th className="text-right py-3 px-2 text-xs font-medium" style={{ color: C.textMuted }}>Entry</th>
                    <th className="text-right py-3 px-2 text-xs font-medium" style={{ color: C.textMuted }}>Exit</th>
                    <th className="text-right py-3 px-2 text-xs font-medium" style={{ color: C.textMuted }}>P&L %</th>
                    <th className="text-left py-3 px-2 text-xs font-medium" style={{ color: C.textMuted }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTradeRecords.map((trade: any, idx: number) => (
                    <tr 
                      key={idx}
                      className="transition-colors"
                      style={{ 
                        borderBottom: `1px solid ${C.border}30`,
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = `${C.teal}08`}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      <td className="py-3 px-2 text-sm" style={{ color: C.textSecondary }}>
                        {trade.entry_datetime ? new Date(trade.entry_datetime).toLocaleDateString() : '-'}
                      </td>
                      <td className="py-3 px-2 text-sm font-medium" style={{ color: C.textPrimary }}>
                        {trade.pair}
                      </td>
                      <td className="py-3 px-2">
                        <span 
                          className="text-xs font-semibold uppercase px-2 py-1 rounded"
                          style={{ 
                            backgroundColor: trade.action === 'long' ? `${C.green}20` : `${C.red}20`,
                            color: trade.action === 'long' ? C.green : C.red
                          }}
                        >
                          {trade.action || '-'}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-sm text-right font-mono" style={{ color: C.textPrimary }}>
                        {formatPrice(trade.entry_price || 0)}
                      </td>
                      <td className="py-3 px-2 text-sm text-right font-mono" style={{ color: C.textPrimary }}>
                        {trade.exit_price ? formatPrice(trade.exit_price) : '-'}
                      </td>
                      <td 
                        className="py-3 px-2 text-sm text-right font-semibold"
                        style={{ color: (trade.pnl_pct || 0) >= 0 ? C.green : C.red }}
                      >
                        {trade.pnl_pct !== null && trade.pnl_pct !== undefined ? formatPercent(trade.pnl_pct) : '-'}
                      </td>
                      <td className="py-3 px-2">
                        <span 
                          className="text-xs px-2 py-1 rounded"
                          style={{ 
                            backgroundColor: trade.status === 'closed' ? `${C.textMuted}20` : 
                                            trade.status === 'open' ? `${C.teal}20` : `${C.amber}20`,
                            color: trade.status === 'closed' ? C.textMuted : 
                                   trade.status === 'open' ? C.teal : C.amber
                          }}
                        >
                          {trade.status || 'closed'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div 
              className="py-12 flex flex-col items-center justify-center"
              style={{ color: C.textMuted }}
            >
              <History className="w-12 h-12 mb-3 opacity-50" />
              <p>No trade history for {selectedPair}</p>
              <p className="text-xs mt-1">Execute some trades to see your history here</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Floating AI Chat Button */}
      {!isChatOpen && (
        <button
          onClick={() => setIsChatOpen(true)}
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 56,
            height: 56,
            borderRadius: '50%',
            backgroundColor: C.teal,
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(20, 184, 166, 0.4)',
            transition: 'transform 0.2s, box-shadow 0.2s',
            zIndex: 50,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.1)'
            e.currentTarget.style.boxShadow = '0 6px 16px rgba(20, 184, 166, 0.5)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)'
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(20, 184, 166, 0.4)'
          }}
        >
          <MessageCircle style={{ width: 24, height: 24, color: C.white }} />
        </button>
      )}

      {/* Chat Drawer Overlay */}
      {isChatOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
          }}
          onClick={() => setIsChatOpen(false)}
        />
      )}

      {/* Chat Drawer - Full Height Sidebar */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: isChatOpen ? 0 : '-480px',
          width: 480,
          height: '100vh',
          backgroundColor: C.bgCard,
          borderLeft: `1px solid ${C.border}`,
          zIndex: 101,
          display: 'flex',
          flexDirection: 'column',
          transition: 'right 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: isChatOpen ? '-4px 0 24px rgba(0, 0, 0, 0.3)' : 'none',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: `1px solid ${C.border}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: `${C.bgCard}99`,
            backdropFilter: 'blur(10px)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                backgroundColor: `${C.teal}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <MessageCircle style={{ width: 20, height: 20, color: C.teal }} />
            </div>
            <div>
              <p style={{ fontWeight: 600, color: C.textPrimary, fontSize: 15 }}>Forex AI Assistant</p>
              <p style={{ fontSize: 12, color: C.textMuted }}>Ask about {selectedPair} & trading</p>
            </div>
          </div>
          <button
            onClick={() => setIsChatOpen(false)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 8,
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = `${C.border}40`
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            <X style={{ width: 20, height: 20, color: C.textMuted }} />
          </button>
        </div>

        {/* Messages Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          {chatMessages.length === 0 && (
            <div style={{ 
              textAlign: 'center', 
              marginTop: 'auto',
              marginBottom: 'auto',
              padding: '40px 20px',
            }}>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 16,
                  backgroundColor: `${C.teal}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 20px',
                }}
              >
                <MessageCircle style={{ width: 32, height: 32, color: C.teal }} />
              </div>
              <p style={{ color: C.textPrimary, fontSize: 16, fontWeight: 500, marginBottom: 8 }}>
                Start a conversation
              </p>
              <p style={{ color: C.textMuted, fontSize: 13, lineHeight: 1.6 }}>
                Ask about {selectedPair} trading, risk analysis, or market insights
              </p>
            </div>
          )}
          {chatMessages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
              }}
            >
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: 16,
                  backgroundColor: msg.role === 'user' ? C.teal : `${C.bgDark}99`,
                  color: msg.role === 'user' ? C.white : C.textPrimary,
                  fontSize: 14,
                  lineHeight: 1.6,
                  boxShadow: msg.role === 'user' ? `0 2px 8px ${C.teal}30` : 'none',
                }}
              >
                {msg.role === 'user' ? (
                  <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                ) : (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p style={{ margin: '0 0 8px 0' }}>{children}</p>,
                      strong: ({ children }) => <strong style={{ color: C.teal, fontWeight: 600 }}>{children}</strong>,
                      em: ({ children }) => <em style={{ color: C.textSecondary }}>{children}</em>,
                      code: ({ children }) => (
                        <code
                          style={{
                            backgroundColor: C.bgCard,
                            padding: '2px 6px',
                            borderRadius: 4,
                            fontSize: 13,
                            fontFamily: 'monospace',
                          }}
                        >
                          {children}
                        </code>
                      ),
                      pre: ({ children }) => (
                        <pre
                          style={{
                            backgroundColor: C.bgCard,
                            padding: 12,
                            borderRadius: 8,
                            overflow: 'auto',
                            fontSize: 13,
                            fontFamily: 'monospace',
                            margin: '8px 0',
                          }}
                        >
                          {children}
                        </pre>
                      ),
                      ul: ({ children }) => (
                        <ul style={{ margin: '8px 0', paddingLeft: 20 }}>{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol style={{ margin: '8px 0', paddingLeft: 20 }}>{children}</ol>
                      ),
                      li: ({ children }) => (
                        <li style={{ marginBottom: 4 }}>{children}</li>
                      ),
                      h1: ({ children }) => (
                        <h1 style={{ fontSize: 18, fontWeight: 600, margin: '12px 0 8px', color: C.teal }}>{children}</h1>
                      ),
                      h2: ({ children }) => (
                        <h2 style={{ fontSize: 16, fontWeight: 600, margin: '10px 0 6px', color: C.teal }}>{children}</h2>
                      ),
                      h3: ({ children }) => (
                        <h3 style={{ fontSize: 14, fontWeight: 600, margin: '8px 0 4px', color: C.teal }}>{children}</h3>
                      ),
                      a: ({ href, children }) => (
                        <a href={href} style={{ color: C.teal, textDecoration: 'underline' }} target="_blank" rel="noopener noreferrer">
                          {children}
                        </a>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote
                          style={{
                            borderLeft: `3px solid ${C.teal}`,
                            paddingLeft: 12,
                            margin: '8px 0',
                            color: C.textSecondary,
                          }}
                        >
                          {children}
                        </blockquote>
                      ),
                      hr: () => (
                        <hr style={{ border: 'none', borderTop: `1px solid ${C.border}`, margin: '12px 0' }} />
                      ),
                      table: ({ children }) => (
                        <table style={{ borderCollapse: 'collapse', width: '100%', margin: '8px 0', fontSize: 13 }}>
                          {children}
                        </table>
                      ),
                      th: ({ children }) => (
                        <th style={{ border: `1px solid ${C.border}`, padding: '6px 10px', backgroundColor: C.bgCard, textAlign: 'left' }}>
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td style={{ border: `1px solid ${C.border}`, padding: '6px 10px' }}>
                          {children}
                        </td>
                      ),
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                )}
              </div>
            </div>
          ))}
          {isChatLoading && (
            <div style={{ alignSelf: 'flex-start', maxWidth: '85%' }}>
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: 16,
                  backgroundColor: `${C.bgDark}99`,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <Loader2 className="animate-spin" style={{ width: 16, height: 16, color: C.teal }} />
                <span style={{ color: C.textMuted, fontSize: 14 }}>Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div
          style={{
            padding: '20px 24px',
            borderTop: `1px solid ${C.border}`,
            display: 'flex',
            gap: 12,
            backgroundColor: `${C.bgCard}99`,
            backdropFilter: 'blur(10px)',
          }}
        >
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyPress={handleChatKeyPress}
            placeholder={`Ask about ${selectedPair}...`}
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: 12,
              border: `1px solid ${C.border}`,
              backgroundColor: C.bgDark,
              color: C.textPrimary,
              fontSize: 14,
              outline: 'none',
              transition: 'border-color 0.2s',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = C.teal
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = C.border
            }}
            disabled={isChatLoading}
          />
          <button
            onClick={handleChatSend}
            disabled={!chatInput.trim() || isChatLoading}
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              backgroundColor: chatInput.trim() && !isChatLoading ? C.teal : C.border,
              border: 'none',
              cursor: chatInput.trim() && !isChatLoading ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              if (chatInput.trim() && !isChatLoading) {
                e.currentTarget.style.backgroundColor = C.tealDark
                e.currentTarget.style.transform = 'scale(1.05)'
              }
            }}
            onMouseLeave={(e) => {
              if (chatInput.trim() && !isChatLoading) {
                e.currentTarget.style.backgroundColor = C.teal
                e.currentTarget.style.transform = 'scale(1)'
              }
            }}
          >
            <Send style={{ width: 18, height: 18, color: C.white }} />
          </button>
        </div>
      </div>
    </div>
  )
}