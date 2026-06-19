"use client"

import { Button } from "@/components/ui/button"
import { ChevronDown } from "lucide-react"
import { stockInfo } from "../data/options-data/stockData"

export function StockHeader() {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-teal-900/40">
      <h1 className="text-2xl md:text-3xl font-bold text-white">
        {stockInfo.ticker} - {stockInfo.companyName}
      </h1>

      <div className="flex items-center gap-3">
        <Button className="bg-teal-500 hover:bg-teal-600 text-white px-6">Buy</Button>
        <Button className="bg-red-500 hover:bg-red-600 text-white px-6">Sell</Button>
        <Button
          variant="outline"
          className="border-teal-600 text-teal-400 hover:bg-teal-950/50 hover:text-teal-300 bg-transparent"
        >
          Compare
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
