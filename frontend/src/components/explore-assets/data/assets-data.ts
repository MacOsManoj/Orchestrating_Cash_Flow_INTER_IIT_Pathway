import type { MarketIndex, Asset, FilterOption } from "./types"

export const marketIndices: MarketIndex[] = [
  {
    id: "1",
    name: "S&P 500",
    value: 5431.6,
    change: 21.43,
    changePercent: 0.4,
    trend: "up",
    chartData: [20, 25, 22, 28, 26, 30, 28, 32, 35, 33, 38, 40],
  },
  {
    id: "2",
    name: "FTSE 100",
    value: 8146.86,
    change: -15.58,
    changePercent: 0.19,
    trend: "down",
    chartData: [40, 38, 42, 35, 38, 32, 35, 30, 33, 28, 30, 25],
  },
  {
    id: "3",
    name: "NASDAQ",
    value: 17667.56,
    change: 59.12,
    changePercent: 0.34,
    trend: "up",
    chartData: [15, 18, 16, 22, 20, 25, 23, 28, 26, 30, 32, 35],
  },
  {
    id: "4",
    name: "NIKKEI 225",
    value: 38720.47,
    change: -65.66,
    changePercent: 0.17,
    trend: "down",
    chartData: [45, 42, 44, 40, 42, 38, 40, 36, 38, 34, 36, 32],
  },
]

export const assetClassOptions: FilterOption[] = [
  { label: "Stocks", value: "stocks" },
  { label: "Bonds", value: "bonds" },
  { label: "Forex", value: "forex" },
]

// Stock-specific filters
export const stockRegionOptions: FilterOption[] = [
  { label: "All Regions", value: "all" },
  { label: "Asia", value: "asia" },
]

export const stockSectorOptions: FilterOption[] = [
  { label: "All Sectors", value: "all" },
  { label: "Technology", value: "tech" },
  { label: "Finance", value: "finance" },
  { label: "Energy", value: "energy" },
  { label: "Healthcare", value: "health" },
  { label: "Consumer", value: "consumer" },
  { label: "Infrastructure", value: "infrastructure" },
  { label: "Materials", value: "materials" },
  { label: "Automotive", value: "automotive" },
  { label: "Diversified", value: "diversified" },
]

// Bond-specific filters  
export const bondRegionOptions: FilterOption[] = [
  { label: "All Regions", value: "all" },
  { label: "Asia", value: "asia" },
]

export const bondSectorOptions: FilterOption[] = [
  { label: "All Bonds", value: "all" },
]

// Forex-specific filters
export const forexRegionOptions: FilterOption[] = [
  { label: "All Pairs", value: "all" },
  { label: "Major Pairs", value: "major" },
  { label: "INR Pairs", value: "inr" },
]
