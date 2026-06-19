"use client"

import { useState } from "react"
import type { TechnicalData, FundamentalData } from "../data/stock-data"

interface TechnicalFundamentalCardProps {
  technicalData: TechnicalData
  fundamentalData: FundamentalData
}

export function TechnicalFundamentalCard({ technicalData, fundamentalData }: TechnicalFundamentalCardProps) {
  const [activeTab, setActiveTab] = useState<"technical" | "fundamental">("technical")

  return (
    <div className="border border-teal-700/50 rounded-lg bg-[#0a2428] overflow-hidden flex-1 flex flex-col">
      <div className="flex border-b border-teal-700/50">
        <button
          onClick={() => setActiveTab("technical")}
          className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
            activeTab === "technical"
              ? "text-white bg-teal-700/30 border-b-2 border-emerald-500"
              : "text-gray-400 hover:text-white hover:bg-teal-700/20"
          }`}
        >
          Technical
        </button>
        <button
          onClick={() => setActiveTab("fundamental")}
          className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
            activeTab === "fundamental"
              ? "text-white bg-teal-700/30 border-b-2 border-emerald-500"
              : "text-gray-400 hover:text-white hover:bg-teal-700/20"
          }`}
        >
          Fundamentals
        </button>
      </div>
      <div className="p-6 flex-1">
        {activeTab === "technical" ? (
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">RSI (14):</span>
              <span className="text-white text-sm">{technicalData.rsi}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">MACD:</span>
              <span className="text-white text-sm">{technicalData.macd}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">50-Day MA:</span>
              <span className="text-white text-sm">{technicalData.movingAverage50}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">200-Day MA:</span>
              <span className="text-white text-sm">{technicalData.movingAverage200}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Support:</span>
              <span className="text-white text-sm">{technicalData.support}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Resistance:</span>
              <span className="text-white text-sm">{technicalData.resistance}</span>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">P/E Ratio:</span>
              <span className="text-white text-sm">{fundamentalData.peRatio}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">P/B Ratio:</span>
              <span className="text-white text-sm">{fundamentalData.pbRatio}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Debt to Equity:</span>
              <span className="text-white text-sm">{fundamentalData.debtToEquity}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Current Ratio:</span>
              <span className="text-white text-sm">{fundamentalData.currentRatio}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">EPS Growth:</span>
              <span className="text-white text-sm">{fundamentalData.epsGrowth}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Revenue Growth:</span>
              <span className="text-white text-sm">{fundamentalData.revenueGrowth}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
