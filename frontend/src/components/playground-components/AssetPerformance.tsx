// src/components/playground-components/AssetPerformance.tsx
"use client"

import React from "react"
import type { ComponentSize } from "../CanvasLayout"

interface AssetPerformanceItem {
  name?: string
  price?: number
  performance?: number // percentage, e.g -5.2 or 3.7
}

interface AssetPerformanceProps {
  title?: string
  subtitle?: string
  assets?: AssetPerformanceItem[]
}

interface AssetPerformanceComponent extends React.FC<AssetPerformanceProps> {
  canvasSize?: ComponentSize
}

export const AssetPerformance: AssetPerformanceComponent = ({
  title = "Asset Performance",
  subtitle = "Key instruments and their recent performance",
  assets = [],
}) => {
  return (
    <div className="w-full h-full bg-[#0d2d2f] rounded-lg p-2 sm:p-2.5 md:p-3 text-white shadow-lg flex flex-col">
      {/* Header - compact */}
      <div className="mb-2 sm:mb-2.5 md:mb-3">
        <h2 className="text-xs sm:text-sm md:text-base font-semibold leading-tight">
          {title}
        </h2>
        <p className="text-[9px] sm:text-[10px] md:text-xs text-gray-400 leading-tight mt-0.5">
          {subtitle}
        </p>
      </div>

      {/* Table - compact */}
      <div className="space-y-0.5 sm:space-y-1 flex-1 overflow-y-auto">
        {/* Header Row - compact */}
        <div className="grid grid-cols-12 gap-2 sm:gap-3 pb-1.5 sm:pb-2 border-b border-gray-700/50 text-[9px] sm:text-[10px] md:text-xs text-gray-400 uppercase tracking-wider sticky top-0 bg-[#0d2d2f] z-10">
          <div className="col-span-5">Asset</div>
          <div className="col-span-3">Price</div>
          <div className="col-span-4">Performance</div>
        </div>

        {/* Data Rows - compact */}
        {assets.map((asset, index) => {
          const price =
            typeof asset.price === "number" && !Number.isNaN(asset.price)
              ? asset.price
              : null

          const perf =
            typeof asset.performance === "number" &&
            !Number.isNaN(asset.performance)
              ? asset.performance
              : null

          const isPositive = (perf ?? 0) >= 0
          const barWidth = perf == null
            ? 0
            : Math.min(100, Math.max(0, Math.abs(perf)))

          return (
            <div
              key={`${asset.name ?? "asset"}-${index}`}
              className="grid grid-cols-12 gap-2 sm:gap-3 items-center py-1 sm:py-1.5 md:py-2 border-b border-gray-700/20 last:border-0"
            >
              {/* Asset name - compact */}
              <div className="col-span-5 text-[10px] sm:text-xs md:text-sm truncate font-medium">
                {asset.name ?? "—"}
              </div>

              {/* Price - compact */}
              <div className="col-span-3 text-[10px] sm:text-xs md:text-sm text-gray-200">
                {price == null
                  ? "—"
                  : price.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
              </div>

              {/* Performance - compact */}
              <div className="col-span-4 flex flex-col gap-0.5 sm:gap-1">
                <div
                  className={`text-[10px] sm:text-xs md:text-sm font-semibold ${
                    perf == null
                      ? "text-gray-400"
                      : isPositive
                        ? "text-[#14b8a6]"
                        : "text-[#ef4444]"
                  }`}
                >
                  {perf == null ? (
                    "—"
                  ) : (
                    <>
                      {isPositive ? "+" : ""}
                      {perf.toFixed(2)}%
                    </>
                  )}
                </div>
                <div className="w-full h-1 sm:h-1.5 bg-gray-800/50 rounded-full overflow-hidden">
                  {perf != null && (
                    <div
                      className={`h-full rounded-full transition-all ${
                        isPositive ? "bg-[#14b8a6]" : "bg-[#ef4444]"
                      }`}
                      style={{ width: `${barWidth}%` }}
                    />
                  )}
                </div>
              </div>
            </div>
          )
        })}

        {assets.length === 0 && (
          <div className="text-center text-gray-500 text-[10px] sm:text-xs py-2 sm:py-3">
            No assets to display
          </div>
        )}
      </div>
    </div>
  )
}

// Default size for dynamic canvas layout
AssetPerformance.canvasSize = "medium"
