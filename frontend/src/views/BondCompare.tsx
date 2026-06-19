"use client"

import React from "react"
import { ArrowLeft, X, TrendingUp, TrendingDown, Plus } from "lucide-react"
import { useMultipleBondDetails, useMultiplePriceStatistics } from "@/queries/bonds_queries"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"

// Chart colors for different bonds - high contrast colors
const CHART_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#A855F7", "#06B6D4", "#EC4899", "#FFFFFF"]

interface BondCompareProps {
  selectedIsins: string[]
  onBack: () => void
  onRemoveBond: (isin: string) => void
  onAddBond?: () => void
}

// Skeleton components
const SkeletonPulse: React.FC<{ className?: string }> = ({ className = "" }) => (
  <div className={`bg-[#1e3a5f] rounded animate-pulse ${className}`} />
)

const ComparisonTableSkeleton: React.FC = () => (
  <div className="bg-card border border-border rounded-xl p-6">
    <SkeletonPulse className="h-6 w-48 mb-6" />
    <div className="space-y-4">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} className="flex gap-4">
          <SkeletonPulse className="h-8 w-32" />
          <SkeletonPulse className="h-8 flex-1" />
          <SkeletonPulse className="h-8 flex-1" />
          <SkeletonPulse className="h-8 flex-1" />
        </div>
      ))}
    </div>
  </div>
)

// Format helpers
function formatCouponRate(rate: number | undefined | null): string {
  if (rate === undefined || rate === null) return "N/A"
  const percentage = rate < 1 ? rate * 100 : rate
  return `${percentage.toFixed(2)}%`
}

function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return "N/A"
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" })
  } catch {
    return dateStr
  }
}

function formatPrice(price: number | undefined | null): string {
  if (price === undefined || price === null) return "N/A"
  return `₹${price.toFixed(2)}`
}

function formatYtm(ytm: number | undefined | null): string {
  if (ytm === undefined || ytm === null) return "N/A"
  return `${(ytm * 100).toFixed(2)}%`
}

// Extract short bond name
function getShortBondName(bondName: string): string {
  const match = bondName.match(/^([^\d]+)/)
  if (match) {
    const name = match[1].trim()
    return name.length > 25 ? name.slice(0, 25) + "..." : name
  }
  return bondName.slice(0, 25)
}

export const BondCompare: React.FC<BondCompareProps> = ({ selectedIsins, onBack, onRemoveBond, onAddBond }) => {
  const [selectedTimePeriod, setSelectedTimePeriod] = React.useState<"1M" | "3M" | "1Y" | "MAX">("1M")
  const timePeriods = ["1M", "3M", "1Y", "MAX"] as const

  // Fetch bond details for all selected bonds
  const { data: bondDetails, isLoading: isLoadingDetails } = useMultipleBondDetails(selectedIsins)
  
  // Fetch price statistics for all selected bonds
  const { data: priceStats, isLoading: isLoadingPrice } = useMultiplePriceStatistics(selectedIsins, selectedTimePeriod)

  const isLoading = isLoadingDetails || isLoadingPrice

  // Prepare chart data - merge all price series by date
  const chartData = React.useMemo(() => {
    if (!priceStats || priceStats.length === 0) return []

    // Get all unique dates
    interface ChartDataPoint {
      date: string;
      displayDate?: string;
      [key: string]: string | number | undefined;
    }
    const dateMap = new Map<string, ChartDataPoint>()
    
    priceStats.forEach((stats, index) => {
      if (!stats?.price_data) return
      stats.price_data.forEach((point) => {
        if (!dateMap.has(point.date)) {
          dateMap.set(point.date, { date: point.date })
        }
        const entry = dateMap.get(point.date)!
        entry[`price_${index}`] = point.price
      })
    })

    // Sort by date and convert to array
    return Array.from(dateMap.values()).sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    ).map((item) => ({
      ...item,
      displayDate: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    }))
  }, [priceStats])

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold mb-2">{payload[0]?.payload?.displayDate}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {bondDetails?.[index] ? getShortBondName(bondDetails[index].bond_name) : `Bond ${index + 1}`}: 
              <span className="font-bold ml-1">₹{entry.value?.toFixed(2)}</span>
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  // Comparison metrics
  const getComparisonMetrics = () => {
    if (!bondDetails) return []
    
    const metrics = [
      {
        label: "Bond Name",
        values: bondDetails.map(b => getShortBondName(b.bond_name)),
        type: "text"
      },
      {
        label: "ISIN",
        values: bondDetails.map(b => b.isin),
        type: "text"
      },
      {
        label: "Coupon Rate",
        values: bondDetails.map(b => formatCouponRate(b.coupon_rate)),
        type: "percent",
        rawValues: bondDetails.map(b => b.coupon_rate)
      },
      {
        label: "Maturity Date",
        values: bondDetails.map(b => formatDate(b.maturity_date)),
        type: "date"
      },
      {
        label: "Last Price",
        values: bondDetails.map(b => formatPrice(b.last_price)),
        type: "price",
        rawValues: bondDetails.map(b => b.last_price)
      },
      {
        label: "YTM",
        values: bondDetails.map(b => formatYtm(b.ytm)),
        type: "percent",
        rawValues: bondDetails.map(b => b.ytm)
      },
      {
        label: "Duration",
        values: bondDetails.map(b => b.duration ? `${b.duration.toFixed(2)} Y` : "N/A"),
        type: "number",
        rawValues: bondDetails.map(b => b.duration)
      },
      {
        label: "Convexity",
        values: bondDetails.map(b => b.convexity?.toFixed(2) ?? "N/A"),
        type: "number",
        rawValues: bondDetails.map(b => b.convexity)
      },
      {
        label: "DV01",
        values: bondDetails.map(b => b.dv01 ? `₹${b.dv01.toFixed(2)}` : "N/A"),
        type: "price",
        rawValues: bondDetails.map(b => b.dv01)
      },
      {
        label: "Z-Spread",
        values: bondDetails.map(b => b.z_spread ? `+${b.z_spread} bps` : "N/A"),
        type: "number",
        rawValues: bondDetails.map(b => b.z_spread)
      },
      {
        label: "VaR (95%)",
        values: bondDetails.map(b => b.var ? `₹${b.var.toFixed(2)}` : "N/A"),
        type: "price",
        rawValues: bondDetails.map(b => b.var)
      },
      {
        label: "Accrued Interest",
        values: bondDetails.map(b => formatPrice(b.accrued_interest)),
        type: "price",
        rawValues: bondDetails.map(b => b.accrued_interest)
      },
    ]
    
    return metrics
  }

  const metrics = getComparisonMetrics()

  // Get best/worst indicators for numeric metrics
  const getBestWorstIndicator = (metric: typeof metrics[0], index: number) => {
    if (!metric.rawValues || metric.type === "text" || metric.type === "date") return null
    
    const validValues = metric.rawValues.filter(v => v !== undefined && v !== null) as number[]
    if (validValues.length < 2) return null
    
    const value = metric.rawValues[index]
    if (value === undefined || value === null) return null
    
    const max = Math.max(...validValues)
    const min = Math.min(...validValues)
    
    // Higher is better for: Coupon Rate, YTM
    // Lower is better for: VaR, Duration (risk)
    const higherIsBetter = ["Coupon Rate", "YTM", "Last Price"].includes(metric.label)
    const lowerIsBetter = ["VaR (95%)", "Duration"].includes(metric.label)
    
    if (higherIsBetter && value === max) {
      return <TrendingUp className="w-4 h-4 text-green-400 ml-1 inline" />
    }
    if (higherIsBetter && value === min) {
      return <TrendingDown className="w-4 h-4 text-red-400 ml-1 inline" />
    }
    if (lowerIsBetter && value === min) {
      return <TrendingUp className="w-4 h-4 text-green-400 ml-1 inline" />
    }
    if (lowerIsBetter && value === max) {
      return <TrendingDown className="w-4 h-4 text-red-400 ml-1 inline" />
    }
    
    return null
  }

  // Price statistics summary
  const getPriceStatsSummary = () => {
    if (!priceStats || priceStats.length === 0) return []
    
    return priceStats.map((stats, index) => ({
      bondName: bondDetails?.[index] ? getShortBondName(bondDetails[index].bond_name) : `Bond ${index + 1}`,
      color: CHART_COLORS[index % CHART_COLORS.length],
      medianPrice: stats?.metrics?.median_price,
      price5th: stats?.metrics?.price_5th_percentile,
      price95th: stats?.metrics?.price_95th_percentile,
      volatility: stats?.metrics?.implied_volatility,
    }))
  }

  const priceStatsSummary = getPriceStatsSummary()

  if (selectedIsins.length === 0) {
    return (
      <div className="min-h-screen bg-background text-white p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-white/70 text-lg mb-2">No bonds selected for comparison</p>
          <button
            onClick={onBack}
            className="px-6 py-2 bg-primary text-black font-semibold rounded-lg hover:bg-primary/80"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-card rounded-lg transition-colors"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">Bond Comparison</h1>
            <p className="text-sm text-white/70">Comparing {selectedIsins.length} bonds</p>
          </div>
        </div>
        {onAddBond && (
          <button
            onClick={onAddBond}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-black font-semibold rounded-lg hover:bg-primary/80 transition-colors"
          >
            <Plus className="w-5 h-5" />
            Add Bond
          </button>
        )}
      </div>

      {/* Selected Bonds Chips */}
      <div className="flex flex-wrap gap-2 mb-6">
        {bondDetails?.map((bond, index) => (
          <div
            key={bond.isin}
            className="flex items-center gap-2 px-3 py-2 rounded-full border"
            style={{ 
              borderColor: CHART_COLORS[index % CHART_COLORS.length],
              backgroundColor: `${CHART_COLORS[index % CHART_COLORS.length]}20`
            }}
          >
            <div 
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
            />
            <span className="text-sm font-medium">{getShortBondName(bond.bond_name)}</span>
            <button
              onClick={() => onRemoveBond(bond.isin)}
              className="hover:bg-white/10 rounded-full p-0.5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-6">
          <ComparisonTableSkeleton />
          <ComparisonTableSkeleton />
        </div>
      ) : (
        <>
          {/* Price Forecast Chart */}
          <div className="bg-card border border-border rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Price Forecast Comparison</h2>
              <div className="flex gap-2">
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
            </div>

            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
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
                  <Legend 
                    formatter={(value) => {
                      const index = parseInt(value.split('_')[1])
                      return bondDetails?.[index] ? getShortBondName(bondDetails[index].bond_name) : value
                    }}
                  />
                  {selectedIsins.map((_, index) => (
                    <Line
                      key={index}
                      type="monotone"
                      dataKey={`price_${index}`}
                      name={`price_${index}`}
                      stroke={CHART_COLORS[index % CHART_COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 6, fill: CHART_COLORS[index % CHART_COLORS.length] }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Price Statistics Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {priceStatsSummary.map((stats, index) => (
              <div 
                key={index} 
                className="bg-card border border-border rounded-xl p-4"
                style={{ borderLeftColor: stats.color, borderLeftWidth: 4 }}
              >
                <p className="text-sm text-white/70 mb-2 truncate">{stats.bondName}</p>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-xs text-white/50">Median Price</p>
                    <p className="text-sm font-semibold">{formatPrice(stats.medianPrice)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-white/50">Volatility</p>
                    <p className="text-sm font-semibold">{stats.volatility?.toFixed(2)}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-white/50">5th %ile</p>
                    <p className="text-sm font-semibold text-red-400">{formatPrice(stats.price5th)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-white/50">95th %ile</p>
                    <p className="text-sm font-semibold text-green-400">{formatPrice(stats.price95th)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Detailed Comparison Table */}
          <div className="bg-card border border-border rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Detailed Comparison</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-white/70 w-40">Metric</th>
                    {bondDetails?.map((bond, index) => (
                      <th 
                        key={bond.isin} 
                        className="text-left py-3 px-4 text-sm font-semibold"
                        style={{ color: CHART_COLORS[index % CHART_COLORS.length] }}
                      >
                        {getShortBondName(bond.bond_name)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((metric, rowIndex) => (
                    <tr 
                      key={metric.label} 
                      className={`border-b border-gray-800 ${rowIndex % 2 === 0 ? 'bg-gray-800/20' : ''}`}
                    >
                      <td className="py-3 px-4 text-sm text-white/70 font-medium">{metric.label}</td>
                      {metric.values.map((value, colIndex) => (
                        <td key={colIndex} className="py-3 px-4 text-sm font-semibold">
                          {value}
                          {getBestWorstIndicator(metric, colIndex)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Risk Comparison Visualization */}
          <div className="grid grid-cols-2 gap-4 mt-6">
            {/* Duration vs Yield */}
            <div className="bg-card border border-border rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Duration vs YTM</h3>
              <div className="space-y-4">
                {bondDetails?.map((bond, index) => {
                  const duration = bond.duration || 0
                  const ytm = bond.ytm ? bond.ytm * 100 : 0
                  const maxDuration = Math.max(...(bondDetails?.map(b => b.duration || 0) || [10]))
                  const maxYtm = Math.max(...(bondDetails?.map(b => (b.ytm || 0) * 100) || [10]))
                  
                  return (
                    <div key={bond.isin}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-white/70 truncate max-w-[150px]">
                          {getShortBondName(bond.bond_name)}
                        </span>
                        <span className="text-xs text-white/50">
                          Duration: {duration.toFixed(2)}Y | YTM: {ytm.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <div className="flex-1">
                          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div 
                              className="h-full rounded-full transition-all duration-500"
                              style={{ 
                                width: `${(duration / maxDuration) * 100}%`,
                                backgroundColor: CHART_COLORS[index % CHART_COLORS.length]
                              }}
                            />
                          </div>
                        </div>
                        <div className="flex-1">
                          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div 
                              className="h-full rounded-full transition-all duration-500"
                              style={{ 
                                width: `${(ytm / maxYtm) * 100}%`,
                                backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                                opacity: 0.6
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Risk Metrics Summary */}
            <div className="bg-card border border-border rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Risk Profile Summary</h3>
              <div className="space-y-4">
                {bondDetails?.map((bond, index) => {
                  const var95 = bond.var || 0
                  const maxVar = Math.max(...(bondDetails?.map(b => b.var || 0) || [100]))
                  const riskLevel = var95 < maxVar * 0.33 ? "Low" : var95 < maxVar * 0.66 ? "Medium" : "High"
                  const riskColor = riskLevel === "Low" ? "text-green-400" : riskLevel === "Medium" ? "text-yellow-400" : "text-red-400"
                  
                  return (
                    <div key={bond.isin} className="flex items-center gap-4">
                      <div 
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{getShortBondName(bond.bond_name)}</p>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-xs text-white/50">VaR (95%)</p>
                          <p className="text-sm font-semibold">₹{var95.toFixed(2)}</p>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs font-semibold ${riskColor} bg-white/5`}>
                          {riskLevel} Risk
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
