import { ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { StockData } from "../data/stock-data"

interface StockHeaderProps {
  data: StockData
}

export function StockHeader({ data }: StockHeaderProps) {
  const isNegative = data.priceChange < 0

  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">{data.name}</h1>
        <div className="flex items-center gap-4">
          <span className="text-4xl font-bold text-white">Rs. {data.price}/-</span>
          <div className="flex items-center gap-2">
            <span className={`text-lg font-semibold ${isNegative ? "text-red-500" : "text-emerald-500"}`}>
              {isNegative ? "▼" : "▲"} {Math.abs(data.priceChangePercent)}%
            </span>
            <span className={`text-lg ${isNegative ? "text-red-500" : "text-emerald-500"}`}>
              {data.priceChange.toFixed(2)} Today
            </span>
          </div>
        </div>
        <p className="text-sm text-gray-400 mt-1">
          {data.timestamp} - {data.currency} - {data.exchange}
        </p>
      </div>
      <div className="flex gap-3">
        <Button className="bg-emerald-500 hover:bg-emerald-600 text-white px-8">Buy</Button>
        <Button className="bg-red-500 hover:bg-red-600 text-white px-8">Sell</Button>
        <Button
          variant="outline"
          className="border-emerald-500 text-emerald-500 hover:bg-emerald-500/10 bg-transparent"
        >
          Compare <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
