"use client"
// Add this import at the top with other recharts imports
// import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, ReferenceLine } from "recharts"
import { useState, useMemo , useRef, useEffect} from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {AreaChart, Area,  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Cell, ReferenceLine } from "recharts"
import { TrendingUp, TrendingDown, AlertTriangle, FileText, Search, Settings, Loader2, MessageCircle,X, Send, Download } from "lucide-react"
import { Input } from "@/components/ui/input"
import { useOpeningClosingBalance, useInAndOutFlow, useCashBalanceForecast, useLiquidityRegime, useCashflowAgentQuery, useMarketRegime } from "@/queries/cash_flow_queries"
import ReactMarkdown from 'react-markdown'


const MAX_HISTORY_LENGTH = 5 // Keep last 10 messages for context


// HARDCODED COLORS - no CSS variables
const C = {
  teal: "#14b8a6",            // Primary accent (added)
  green: "#22c55e",
  red: "#ef4444",
  amber: "#f59e0b",
  blue: "#3b82f6",
  white: "#ffffff",
  textPrimary: "#f1f5f9",     // Changed from #e2e8f0
  textSecondary: "#94a3b8",
  textMuted: "#64748b",
  bgDark: "#0b1623",          // Changed from #0f172a
  bgCard: "#0d1f2d",          // Changed from #1e293b
  border: "#145b5b",          // Changed from #334155
  // Stacked bar colors for inflows
  deposits: "#2dd4bf",        // Teal
  loanRepayments: "#14b8a6",  // Darker teal
  investmentIncome: "#0d9488", // Even darker teal
  // Stacked bar colors for outflows
  withdrawals: "#f87171",     // Light red
  loanDisbursements: "#ef4444", // Red
  debtService: "#dc2626",     // Dark red
}

// Format number to currency
const formatCurrency = (value: number) => {
  if (value === null || value === undefined || isNaN(value)) return '$0'
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`
  } else if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`
  }
  return `$${value.toFixed(2)}`
}

const formatCurrencyFull = (value: number) => {
  if (value === null || value === undefined || isNaN(value)) return '$0'
  return `$${value.toLocaleString()}`
}

// Transform API data to stacked chart format
const transformInOutFlowData = (rawData: any) => {
  if (!rawData) {
    console.log('transformInOutFlowData: No data received')
    return []
  }

  let data = rawData
  if (typeof rawData === 'string') {
    try {
      data = JSON.parse(rawData)
      console.log('transformInOutFlowData: Parsed JSON string')
    } catch (e) {
      console.error('transformInOutFlowData: Failed to parse JSON', e)
      return []
    }
  }

  console.log('transformInOutFlowData: Data structure', data)

  const weeks = ['Fourth Last Week', 'Third Last Week', 'Second Last Week', 'Last Week']

  const result = weeks.map((week, index) => {
    // Inflow categories (positive, stacked above zero)
    const deposits = data['Total Deposit']?.[week] || 0
    const loanRepayments = data['Job Income']?.[week] || 0  // Mapping Job Income to Loan Repayments
    const investmentIncome = data['Interest']?.[week] || 0
    const loans = data['Loans']?.[week] || 0

    // Outflow categories (negative, stacked below zero)
    const withdrawals = -(data['Online Withdrawal']?.[week] || 0)
    const loanDisbursements = -(data['Offline Withdrawal']?.[week] || 0)
    const debtService = 0 // No direct mapping, kept as placeholder

    const totalInflows = deposits + loanRepayments + investmentIncome + loans
    const totalOutflows = Math.abs(withdrawals) + Math.abs(loanDisbursements) + Math.abs(debtService)

    return {
      week: `Week ${index + 1}`,
      weekLabel: week,
      // Inflows (positive stacked)
      deposits,
      loanRepayments,
      investmentIncome,
      // Outflows (negative stacked)
      withdrawals,
      loanDisbursements,
      debtService,
      // Totals for tooltip
      totalInflows,
      totalOutflows,
      net: totalInflows - totalOutflows,
    }
  })

  console.log('transformInOutFlowData: Result', result)
  return result
}

// Custom tooltip component
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div style={{
        backgroundColor: C.bgCard,
        border: `1px solid ${C.border}`,
        borderRadius: 8,
        padding: 12,
        zIndex: 1000,
      }}>
        <p style={{ color: C.textPrimary, fontWeight: 600, marginBottom: 8 }}>{data.week}</p>
        
        <p style={{ color: C.green, fontSize: 14, fontWeight: 500 }}>Inflows: {formatCurrency(data.totalInflows)}</p>
        {data.deposits > 0 && (
          <p style={{ color: C.textMuted, fontSize: 12, marginLeft: 8 }}>• Deposits: {formatCurrency(data.deposits)}</p>
        )}
        {data.loanRepayments > 0 && (
          <p style={{ color: C.textMuted, fontSize: 12, marginLeft: 8 }}>• Loan Repayments: {formatCurrency(data.loanRepayments)}</p>
        )}
        {data.investmentIncome > 0 && (
          <p style={{ color: C.textMuted, fontSize: 12, marginLeft: 8 }}>• Investment Income: {formatCurrency(data.investmentIncome)}</p>
        )}
        
        <p style={{ color: C.red, fontSize: 14, fontWeight: 500, marginTop: 8 }}>Outflows: {formatCurrency(data.totalOutflows)}</p>
        {Math.abs(data.withdrawals) > 0 && (
          <p style={{ color: C.textMuted, fontSize: 12, marginLeft: 8 }}>• Withdrawals: {formatCurrency(Math.abs(data.withdrawals))}</p>
        )}
        {Math.abs(data.loanDisbursements) > 0 && (
          <p style={{ color: C.textMuted, fontSize: 12, marginLeft: 8 }}>• Loan Disbursements: {formatCurrency(Math.abs(data.loanDisbursements))}</p>
        )}
        {Math.abs(data.debtService) > 0 && (
          <p style={{ color: C.textMuted, fontSize: 12, marginLeft: 8 }}>• Debt Service: {formatCurrency(Math.abs(data.debtService))}</p>
        )}
        
        <p style={{
          color: data.net >= 0 ? C.green : C.red,
          fontWeight: 600,
          marginTop: 8,
          fontSize: 14
        }}>
          Net: {data.net >= 0 ? '+' : ''}{formatCurrency(data.net)}
        </p>
      </div>
    )
  }
  return null
}

export function Performance() {

  const [isChatOpen, setIsChatOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState("")
  const [isDownloading, setIsDownloading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { data: ocbalData, isLoading: ocbalLoading } = useOpeningClosingBalance()
  const { data: inOutFlowData, isLoading: inOutFlowLoading, error: inOutFlowError } = useInAndOutFlow()
  const { data: forecastData, isLoading: forecastLoading } = useCashBalanceForecast()
  const { data: liquidityRegime, isLoading: regimeLoading } = useLiquidityRegime()
  const { data: marketRegime, isLoading: marketRegimeLoading } = useMarketRegime()

  const agentMutation = useCashflowAgentQuery()


  const getMarketRegimeColor = (regime: string) => {
    switch (regime) {
      case 'High': return C.green
      case 'Medium': return C.amber
      case 'Low': return C.red
      default: return C.textMuted
    }
  }


  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  
  const handleSendMessage = async () => {
    if (!inputValue.trim() || agentMutation.isPending) return

    const userMessage = inputValue.trim()
    setInputValue("")
    
    const newUserMessage = { role: 'user', content: userMessage }
    setMessages(prev => [...prev, newUserMessage])

    // Get recent history for context (excluding the message we just added)
    const recentHistory = messages.slice(-MAX_HISTORY_LENGTH)

    try {
      const response = await agentMutation.mutateAsync({
        query: userMessage,
        history: recentHistory,
      })
      const assistantMessage = { 
        role: 'assistant', 
        content: response.result || 'No response from agent.' 
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = { 
        role: 'assistant', 
        content: 'Sorry, there was an error processing your request.' 
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleDownloadReport = async () => {
    if (isDownloading) return
    
    setIsDownloading(true)
    try {
      const API_BASE = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/cashflow`
      const response = await fetch(`${API_BASE}/market-report/markdown?download=true`)
      
      if (!response.ok) {
        throw new Error('Failed to download report')
      }
      
      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = 'market_report.md'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      // Create blob and download
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error downloading report:', error)
      alert('Failed to download report. Please try again.')
    } finally {
      setIsDownloading(false)
    }
  }


  // Debug log
  console.log('Raw inOutFlowData:', inOutFlowData)
  console.log('inOutFlowData type:', typeof inOutFlowData)
  console.log('inOutFlowError:', inOutFlowError)

  // Transform with useMemo to avoid re-computing on every render
  const chartData = useMemo(() => {
    return transformInOutFlowData(inOutFlowData)
  }, [inOutFlowData])

  console.log('chartData:', chartData)

  // Calculate Y-axis domain based on data
  const yAxisDomain = useMemo(() => {
    if (chartData.length === 0) return [-10000000, 10000000]
    
    let maxInflow = 0
    let maxOutflow = 0
    
    chartData.forEach(d => {
      const inflow = d.deposits + d.loanRepayments + d.investmentIncome
      const outflow = Math.abs(d.withdrawals) + Math.abs(d.loanDisbursements) + Math.abs(d.debtService)
      maxInflow = Math.max(maxInflow, inflow)
      maxOutflow = Math.max(maxOutflow, outflow)
    })
    
    const maxValue = Math.max(maxInflow, maxOutflow)
    const padding = maxValue * 0.1
    
    return [-(maxOutflow + padding), maxInflow + padding]
  }, [chartData])

  // Build alerts from liquidity regime API response
  const alerts = useMemo(() => {
    const alertList: Array<{
      type: 'error' | 'warning' | 'info';
      title: string;
      description: string;
      confidence?: number;
      features?: any;
    }> = [];

    // Market Regime explanation alert
    if (marketRegime?.regime_explanation) {
      const regimeType = marketRegime.regime === 'High' ? 'info' : marketRegime.regime === 'Medium' ? 'warning' : 'error';
      alertList.push({
        type: regimeType,
        title: 'Market Regime',
        description: marketRegime.regime_explanation,
      });
    }

    // VIX indicator alert
    if (marketRegime?.indicators?.vix) {
      const vix = marketRegime.indicators.vix;
      // VIX below 15 is complacent, above 25 is fearful
      const vixType = vix.value < 15 ? 'warning' : vix.value > 25 ? 'error' : 'info';
      alertList.push({
        type: vixType,
        title: `VIX: ${vix.value.toFixed(2)}`,
        description: vix.explanation,
      });
    }

    // Net Flow indicator alert
    if (marketRegime?.indicators?.net_flow) {
      const flow = marketRegime.indicators.net_flow;
      const flowType = flow.value > 0 ? 'info' : flow.value < -1000 ? 'error' : 'warning';
      alertList.push({
        type: flowType,
        title: `Net Flow: ${flow.value >= 0 ? '+' : ''}${formatCurrency(flow.value)}`,
        description: flow.explanation,
      });
    }

    // Advance/Decline Ratio alert
    if (marketRegime?.indicators?.ad_ratio) {
      const ad = marketRegime.indicators.ad_ratio;
      const adType = ad.value > 1.2 ? 'info' : ad.value < 0.8 ? 'error' : 'warning';
      alertList.push({
        type: adType,
        title: `A/D Ratio: ${ad.value.toFixed(2)}`,
        description: ad.explanation,
      });
    }

    // 10Y Bond Yield alert
    if (marketRegime?.indicators?.bond_10y) {
      const bond = marketRegime.indicators.bond_10y;
      const changeStr = bond.day_change !== undefined 
        ? ` (${bond.day_change >= 0 ? '+' : ''}${bond.day_change.toFixed(2)}%)`
        : '';
      alertList.push({
        type: 'info',
        title: `10Y Yield: ${bond.yield?.toFixed(2) ?? bond.value?.toFixed(2)}%${changeStr}`,
        description: bond.explanation,
      });
    }

    // Liquidity regime alert
    if (liquidityRegime?.alert_status) {
      alertList.push({
        type: 'error',
        title: 'Liquidity Stress Alert',
        description: liquidityRegime.message,
        confidence: liquidityRegime.current_regime_prob,
        features: liquidityRegime.features_used,
      });
    } else if (liquidityRegime) {
      alertList.push({
        type: 'info',
        title: 'Liquidity Status Normal',
        description: 'No critical liquidity issues detected.',
        confidence: liquidityRegime.current_regime_prob,
      });
    }

    return alertList;
  }, [marketRegime, liquidityRegime]);

  const isLoading = ocbalLoading || inOutFlowLoading || forecastLoading || regimeLoading

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: C.bgDark, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 className="h-8 w-8 animate-spin" style={{ color: C.blue }} />
      </div>
    )
  }

  const regimeStatus = liquidityRegime?.alert_status ? "Stress" : "Normal"
  const regimeColor = liquidityRegime?.alert_status ? C.red : C.green

  // Check if chart has valid data
  const hasChartData = chartData.length > 0 && chartData.some(d => d.totalInflows > 0 || d.totalOutflows > 0)

  return (
    <div style={{ minHeight: '100vh', backgroundColor: C.bgDark, color: C.textPrimary }}>


      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Title */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 style={{ fontSize: 30, fontWeight: 600, color: C.textPrimary, marginBottom: 8 }}>Cash Forecasting Dashboard</h1>
            <p style={{ fontSize: 14, color: C.textMuted }}>Liquidity Management and Regulatory Compliance Overview</p>
          </div>
          <button
            onClick={handleDownloadReport}
            disabled={isDownloading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 16px',
              borderRadius: 8,
              backgroundColor: isDownloading ? C.border : C.teal,
              border: 'none',
              color: C.white,
              fontSize: 14,
              fontWeight: 500,
              cursor: isDownloading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              opacity: isDownloading ? 0.6 : 1,
            }}
            onMouseEnter={(e) => {
              if (!isDownloading) {
                e.currentTarget.style.backgroundColor = '#0d9488'
                e.currentTarget.style.transform = 'translateY(-1px)'
              }
            }}
            onMouseLeave={(e) => {
              if (!isDownloading) {
                e.currentTarget.style.backgroundColor = C.teal
                e.currentTarget.style.transform = 'translateY(0)'
              }
            }}
          >
            {isDownloading ? (
              <>
                <Loader2 className="animate-spin" style={{ width: 16, height: 16 }} />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <Download style={{ width: 16, height: 16 }} />
                <span>Download Market Report</span>
              </>
            )}
          </button>
        </div>
        

        {/* Insights Cards */}
        <div className="mb-8">
          <div className="mb-4 flex items-center gap-2">
            <div style={{ height: 8, width: 8, borderRadius: '50%', backgroundColor: C.green }} />
            <h2 style={{ fontSize: 18, fontWeight: 600, color: C.textPrimary }}>Insights</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {/* Opening Balance */}
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ fontSize: 14, fontWeight: 400, color: C.textMuted }}>Opening Cash Balance</CardTitle>
              </CardHeader>
              <CardContent>
                <p style={{ fontSize: 24, fontWeight: 600, color: C.textPrimary }}>
                  {ocbalData ? formatCurrency(ocbalData.opening_balance) : '$0'}
                </p>
                <p style={{ fontSize: 12, color: C.textMuted, marginTop: 4 }}>{ocbalData?.date || ''}</p>
              </CardContent>
            </Card>

            {/* Ending Balance */}
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ fontSize: 14, fontWeight: 400, color: C.textMuted }}>Ending Cash Balance</CardTitle>
              </CardHeader>
              <CardContent>
                <p style={{ fontSize: 24, fontWeight: 600, color: C.textPrimary }}>
                  {ocbalData ? formatCurrency(ocbalData.closing_balance) : '$0'}
                </p>
                <p style={{ fontSize: 12, color: C.textMuted, marginTop: 4 }}>{ocbalData?.date || ''}</p>
              </CardContent>
            </Card>

            {/* Net Cash Flow */}
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ fontSize: 14, fontWeight: 400, color: C.textMuted }}>Net Cash Flow</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  {ocbalData?.['net-cash-flow'] >= 0 ? (
                    <TrendingUp style={{ height: 20, width: 20, color: C.green }} />
                  ) : (
                    <TrendingDown style={{ height: 20, width: 20, color: C.red }} />
                  )}
                  <p style={{ fontSize: 24, fontWeight: 600, color: ocbalData?.['net-cash-flow'] >= 0 ? C.green : C.red }}>
                    {ocbalData ? `${ocbalData['net-cash-flow'] >= 0 ? '+' : ''}${formatCurrency(ocbalData['net-cash-flow'])}` : '$0'}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Liquidity Buffer */}
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ fontSize: 14, fontWeight: 400, color: C.textMuted }}>Market Regime</CardTitle>
              </CardHeader>
              <CardContent>
                <p style={{ fontSize: 24, fontWeight: 600, color: getMarketRegimeColor(marketRegime?.regime), textTransform: 'capitalize' }}>
                  {marketRegime?.regime || 'N/A'}
                </p>
                {marketRegime?.score !== undefined && (
                  <p style={{ fontSize: 12, color: C.textMuted, marginTop: 4 }}>
                    Score: {marketRegime.score}/100
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Liquidity Regime */}
            <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
              <CardHeader className="pb-2">
                <CardTitle style={{ fontSize: 14, fontWeight: 400, color: C.textMuted }}>Liquidity Regime</CardTitle>
              </CardHeader>
              <CardContent>
                <p style={{ fontSize: 24, fontWeight: 600, color: regimeColor, textTransform: 'capitalize' }}>
                  {regimeStatus}
                </p>
                {liquidityRegime?.current_regime_prob && (
                  <p style={{ fontSize: 12, color: C.textMuted, marginTop: 4 }}>
                    Confidence: {(liquidityRegime.current_regime_prob * 100).toFixed(1)}%
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Charts and Alerts */}
        <div className="mb-8 grid gap-4 lg:grid-cols-3">
          {/* Chart */}
          <Card className="lg:col-span-2" style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
            <CardHeader>
              <CardTitle style={{ color: C.textPrimary }}>Inflows vs Outflows</CardTitle>
              <div className="mt-4 flex flex-wrap gap-4">
                {/* Inflow legend items */}
                <div className="flex items-center gap-2">
                  <div style={{ height: 12, width: 12, borderRadius: 2, backgroundColor: C.deposits }} />
                  <span style={{ fontSize: 12, color: C.textSecondary }}>Deposits</span>
                </div>
                <div className="flex items-center gap-2">
                  <div style={{ height: 12, width: 12, borderRadius: 2, backgroundColor: C.loanRepayments }} />
                  <span style={{ fontSize: 12, color: C.textSecondary }}>Loan Repayments</span>
                </div>
                <div className="flex items-center gap-2">
                  <div style={{ height: 12, width: 12, borderRadius: 2, backgroundColor: C.investmentIncome }} />
                  <span style={{ fontSize: 12, color: C.textSecondary }}>Investment Income</span>
                </div>
                {/* Outflow legend items */}
                <div className="flex items-center gap-2">
                  <div style={{ height: 12, width: 12, borderRadius: 2, backgroundColor: C.withdrawals }} />
                  <span style={{ fontSize: 12, color: C.textSecondary }}>Withdrawals</span>
                </div>
                <div className="flex items-center gap-2">
                  <div style={{ height: 12, width: 12, borderRadius: 2, backgroundColor: C.loanDisbursements }} />
                  <span style={{ fontSize: 12, color: C.textSecondary }}>Loan Disbursements</span>
                </div>
                <div className="flex items-center gap-2">
                  <div style={{ height: 12, width: 12, borderRadius: 2, backgroundColor: C.debtService }} />
                  <span style={{ fontSize: 12, color: C.textSecondary }}>Debt Service</span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {hasChartData ? (
                <ResponsiveContainer width="100%" height={550}>
                  <BarChart 
                    data={chartData} 
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    stackOffset="sign"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                    <XAxis
                      dataKey="week"
                      stroke={C.textMuted}
                      tick={{ fill: C.textSecondary, fontSize: 12 }}
                      axisLine={{ stroke: C.border }}
                      tickLine={{ stroke: C.border }}
                    />
                    <YAxis
                      stroke={C.textMuted}
                      tick={{ fill: C.textSecondary, fontSize: 12 }}
                      tickFormatter={(v) => {
                        const absV = Math.abs(v)
                        if (absV >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
                        if (absV >= 1_000) return `${(v / 1_000).toFixed(0)}K`
                        return v.toString()
                      }}
                      axisLine={{ stroke: C.border }}
                      tickLine={{ stroke: C.border }}
                      width={60}
                      domain={yAxisDomain}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(51, 65, 85, 0.3)' }} />
                    <ReferenceLine y={0} stroke={C.textMuted} strokeWidth={1} />
                    
                    {/* Inflow bars (positive, stacked) */}
                    <Bar
                      dataKey="deposits"
                      stackId="stack"
                      fill={C.deposits}
                      name="Deposits"
                    />
                    <Bar
                      dataKey="loanRepayments"
                      stackId="stack"
                      fill={C.loanRepayments}
                      name="Loan Repayments"
                    />
                    <Bar
                      dataKey="investmentIncome"
                      stackId="stack"
                      fill={C.investmentIncome}
                      name="Investment Income"
                    />
                    
                    {/* Outflow bars (negative, stacked) */}
                    <Bar
                      dataKey="withdrawals"
                      stackId="stack"
                      fill={C.withdrawals}
                      name="Withdrawals"
                    />
                    <Bar
                      dataKey="loanDisbursements"
                      stackId="stack"
                      fill={C.loanDisbursements}
                      name="Loan Disbursements"
                    />
                    <Bar
                      dataKey="debtService"
                      stackId="stack"
                      fill={C.debtService}
                      name="Debt Service"
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 350, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: C.textMuted }}>
                  <p>No flow data available</p>
                  <p style={{ fontSize: 12, marginTop: 8 }}>
                    {inOutFlowError ? `Error: ${inOutFlowError}` : 'Check console for debug info'}
                  </p>
                  {inOutFlowData && (
                    <pre style={{ fontSize: 10, marginTop: 8, maxWidth: '100%', overflow: 'auto', padding: 8, backgroundColor: C.bgDark, borderRadius: 4 }}>
                      {typeof inOutFlowData === 'string' ? inOutFlowData.slice(0, 200) : JSON.stringify(inOutFlowData, null, 2).slice(0, 200)}...
                    </pre>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Alerts Panel */}
          <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
            <CardHeader>
              <CardTitle style={{ color: C.textPrimary }}>Alerts & Insights</CardTitle>
              <CardDescription style={{ color: C.textMuted }}>
                Important notifications and recommendations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {alerts.map((alert, index) => {
                const alertColor = alert.type === "error" ? C.red : alert.type === "warning" ? C.amber : C.green
                return (
                  <div
                    key={index}
                    style={{
                      borderRadius: 8,
                      border: `1px solid ${alertColor}50`,
                      backgroundColor: `${alertColor}15`,
                      padding: 12,
                    }}
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <div style={{
                        borderRadius: 4,
                        backgroundColor: alertColor,
                        padding: '2px 6px',
                        fontSize: 12,
                        fontWeight: 500,
                        color: C.white,
                      }}>
                        {alert.type === "error" ? "!" : alert.type === "warning" ? "⚠" : "✓"}
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 500, color: alertColor }}>{alert.title}</span>
                    </div>
                    <p style={{ fontSize: 12, color: C.textMuted }}>{alert.description}</p>
                    {alert.confidence && (
                      <p style={{ fontSize: 11, color: C.textMuted, marginTop: 4 }}>
                        Probability: {(alert.confidence * 100).toFixed(1)}%
                      </p>
                    )}
                    {alert.features && (
                      <div style={{ marginTop: 8, fontSize: 11, color: C.textMuted }}>
                        <p>• 30-day Trend: {(alert.features['30_day_trend'] * 100).toFixed(2)}%</p>
                        <p>• Volatility: {(alert.features['30_day_volatility'] * 100).toFixed(2)}%</p>
                        <p>• Panic Index: {(alert.features['30_day_panic_index'] * 100).toFixed(2)}%</p>
                      </div>
                    )}
                  </div>
                )
              })}
            </CardContent>
          </Card>
        </div>

        
  
        {/* Cash Balance Forecast Chart */}
         <Card className="mb-8" style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle style={{ color: C.textPrimary }}>Cash Balance Forecast</CardTitle>
              
            </div>
          </CardHeader>
           <CardContent>
            {forecastData?.result && forecastData.result.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart
                  data={forecastData.result.map((value: number, index: number) => ({
                    day: index + 1,
                    value: value,
                  }))}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <defs>
                    <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={C.deposits} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={C.deposits} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                  <XAxis
                    dataKey="day"
                    stroke={C.textMuted}
                    tick={{ fill: C.textSecondary, fontSize: 12 }}
                    axisLine={{ stroke: C.border }}
                    tickLine={{ stroke: C.border }}
                    tickFormatter={(v) => `Day ${v}`}
                    interval={4}
                  />
                  <YAxis
                    stroke={C.textMuted}
                    tick={{ fill: C.textSecondary, fontSize: 12 }}
                    tickFormatter={(v) => {
                      if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
                      if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
                      return v.toString()
                    }}
                    axisLine={{ stroke: C.border }}
                    tickLine={{ stroke: C.border }}
                    width={60}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload
                        return (
                          <div style={{
                            backgroundColor: C.bgCard,
                            border: `1px solid ${C.border}`,
                            borderRadius: 8,
                            padding: 12,
                          }}>
                            <p style={{ color: C.textPrimary, fontWeight: 600 }}>Day {data.day}</p>
                            <p style={{ color: C.deposits, fontSize: 14, marginTop: 4 }}>
                              Balance: {formatCurrency(data.value)}
                            </p>
                          </div>
                        )
                      }
                      return null
                    }}
                    cursor={{ stroke: C.textMuted, strokeDasharray: '3 3' }}
                  />
                  {/* Minimum Liquidity Reference Line - 70% of average */}
                  <ReferenceLine
                    y={forecastData.result.reduce((sum: number, val: number) => sum + val, 0) / forecastData.result.length * 0.7}
                    stroke={C.amber}
                    strokeDasharray="5 5"
                    label={{
                      value: 'Minimum Liquidity',
                      position: 'right',
                      fill: C.amber,
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke={C.deposits}
                    strokeWidth={2}
                    fill="url(#forecastGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.textMuted }}>
                No forecast data available
              </div>
            )}
          </CardContent>
        </Card>


        {/* Forecast Table */}
        {/* <Card style={{ backgroundColor: C.bgCard, border: `1px solid ${C.border}` }}>
          <CardHeader>
            <CardTitle style={{ color: C.textPrimary }}>Cash Flow Forecast Details (Next 30 Days)</CardTitle>
            <CardDescription style={{ color: C.textMuted }}>
              Daily breakdown of forecasted cash movements
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto max-h-96">
              <table className="w-full">
                <thead style={{ position: 'sticky', top: 0, backgroundColor: C.bgCard }}>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    <th style={{ padding: 12, textAlign: 'left', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', color: C.textMuted }}>Date</th>
                    <th style={{ padding: 12, textAlign: 'left', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', color: C.textMuted }}>Opening Balance</th>
                    <th style={{ padding: 12, textAlign: 'left', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', color: C.green }}>Predicted Inflows</th>
                    <th style={{ padding: 12, textAlign: 'left', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', color: C.red }}>Predicted Outflows</th>
                    <th style={{ padding: 12, textAlign: 'left', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', color: C.textMuted }}>Net Cash Flow</th>
                    <th style={{ padding: 12, textAlign: 'left', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', color: C.textMuted }}>Closing Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastData?.forecasts?.map((row: any, index: number) => (
                    <tr key={index} style={{ borderBottom: `1px solid ${C.border}50` }}>
                      <td style={{ padding: 12, fontSize: 14, color: C.textPrimary }}>{row.date}</td>
                      <td style={{ padding: 12, fontSize: 14, color: C.textPrimary }}>{formatCurrencyFull(row.opening_balance)}</td>
                      <td style={{ padding: 12, fontSize: 14, color: C.green }}>
                        <span className="inline-flex items-center gap-1">
                          <TrendingUp style={{ height: 12, width: 12 }} />
                          {formatCurrencyFull(row.predicted_inflows)}
                        </span>
                      </td>
                      <td style={{ padding: 12, fontSize: 14, color: C.red }}>
                        <span className="inline-flex items-center gap-1">
                          <TrendingDown style={{ height: 12, width: 12 }} />
                          {formatCurrencyFull(row.predicted_outflows)}
                        </span>
                      </td>
                      <td style={{ padding: 12, fontSize: 14, fontWeight: 500, color: row.net_cash_flow >= 0 ? C.green : C.red }}>
                        {row.net_cash_flow >= 0 ? '+' : ''}{formatCurrencyFull(row.net_cash_flow)}
                      </td>
                      <td style={{ padding: 12, fontSize: 14, color: C.textPrimary }}>{formatCurrencyFull(row.closing_balance)}</td>
                    </tr>
                  ))}
                  {(!forecastData?.forecasts || forecastData.forecasts.length === 0) && (
                    <tr>
                      <td colSpan={6} style={{ padding: 24, textAlign: 'center', color: C.textMuted }}>
                        No forecast data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card> */}
      </main>
     
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
              <p style={{ fontWeight: 600, color: C.textPrimary, fontSize: 15 }}>Cash Flow Agent</p>
              <p style={{ fontSize: 12, color: C.textMuted }}>Ask about liquidity & forecasts</p>
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
          {messages.length === 0 && (
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
                Ask about cash flow forecasts, liquidity status, or financial insights
              </p>
            </div>
          )}
          {messages.map((msg, idx) => (
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
          {agentMutation.isPending && (
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
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about cash flow..."
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
            disabled={agentMutation.isPending}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || agentMutation.isPending}
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              backgroundColor: inputValue.trim() && !agentMutation.isPending ? C.teal : C.border,
              border: 'none',
              cursor: inputValue.trim() && !agentMutation.isPending ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              if (inputValue.trim() && !agentMutation.isPending) {
                e.currentTarget.style.backgroundColor = C.tealDark
                e.currentTarget.style.transform = 'scale(1.05)'
              }
            }}
            onMouseLeave={(e) => {
              if (inputValue.trim() && !agentMutation.isPending) {
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