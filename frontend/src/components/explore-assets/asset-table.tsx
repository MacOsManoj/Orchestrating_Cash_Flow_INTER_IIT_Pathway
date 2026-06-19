"use client"

import type React from "react"

import { useState } from "react"
import type { Asset } from "./data/types"
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react"
import { useAsset } from "@/context/AssetContext"

interface AssetTableProps {
  assets: Asset[]
  assetType: string
}

type SortDirection = "asc" | "desc" | null

export function AssetTable({ assets, assetType }: AssetTableProps) {
  const [sortField, setSortField] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)
  const [selectedRow, setSelectedRow] = useState<string | null>(null)
  const { navigateToAsset } = useAsset()

  const handleRowClick = (asset: Asset) => {
    setSelectedRow(selectedRow === asset.id ? null : asset.id)
    // Navigate to asset detail page
    if (navigateToAsset) {
      navigateToAsset(asset)
    }
  }

  const handleSort = (field: string) => {
    if (sortField === field) {
      if (sortDirection === "asc") {
        setSortDirection("desc")
      } else if (sortDirection === "desc") {
        setSortField(null)
        setSortDirection(null)
      } else {
        setSortDirection("asc")
      }
    } else {
      setSortField(field)
      setSortDirection("asc")
    }
  }

  const sortedAssets = [...assets].sort((a, b) => {
    if (!sortField || !sortDirection) return 0

    let aVal: string | number | undefined = (a as unknown as Record<string, unknown>)[sortField] as string | number | undefined
    let bVal: string | number | undefined = (b as unknown as Record<string, unknown>)[sortField] as string | number | undefined

    if (aVal === undefined || bVal === undefined) return 0

    if (typeof aVal === "string" && aVal.includes("%")) {
      aVal = Number.parseFloat(aVal)
      bVal = Number.parseFloat(bVal as string)
    }

    if (typeof aVal === "string") {
      return sortDirection === "asc" ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal)
    }

    return sortDirection === "asc" ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
  })

  const SortIcon = ({ field }: { field: string }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 opacity-40" />
    if (sortDirection === "asc") return <ArrowUp className="w-3 h-3 text-[#14b8a6]" />
    return <ArrowDown className="w-3 h-3 text-[#14b8a6]" />
  }

  const HeaderCell = ({
    field,
    children,
    center = false,
  }: { field: string; children: React.ReactNode; center?: boolean }) => (
    <th
      onClick={() => handleSort(field)}
      className={`${center ? "text-center" : "text-left"} text-[#6b7a8f] text-xs font-medium uppercase tracking-wider px-4 py-3 cursor-pointer hover:text-[#e2e8f0] transition-colors`}
    >
      <div className={`flex items-center gap-2 ${center ? "justify-center" : ""}`}>
        {children}
        <SortIcon field={field} />
      </div>
    </th>
  )

  // Render different columns based on asset type
  const renderBondsTable = () => (
    <table className="w-full">
      <thead>
        <tr className="bg-[#0a1018] border-b border-[#1e3a5f]">
          <HeaderCell field="name">Bond Name</HeaderCell>
          <HeaderCell field="priceOfPar" center>
            Price (% of Par)
          </HeaderCell>
          <HeaderCell field="yieldToMaturity" center>
            Yield to Maturity (YTM)
          </HeaderCell>
          <HeaderCell field="coupon" center>
            Coupon
          </HeaderCell>
          <HeaderCell field="maturityDate" center>
            Maturity Date
          </HeaderCell>
          <HeaderCell field="duration" center>
            Duration
          </HeaderCell>
          <HeaderCell field="changeBps" center>
            Change (BPS)
          </HeaderCell>
        </tr>
      </thead>
      <tbody className="divide-y divide-[#1e3a5f]/50">
        {sortedAssets.map((asset) => (
          <tr
            key={asset.id}
            onClick={() => handleRowClick(asset)}
            className={`cursor-pointer transition-colors duration-150 ${selectedRow === asset.id ? "bg-[#14b8a6]/5 border-l-2 border-l-[#14b8a6]" : "hover:bg-[#0f1a24]"}`}
          >
            <td className="px-4 py-4">
              <div>
                <p className="text-[#e2e8f0] font-medium">{asset.name}</p>
                <p className="text-[#6b7a8f] text-sm">{asset.ticker}</p>
              </div>
            </td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.priceOfPar?.toFixed(2)}</td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.yieldToMaturity}</td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.coupon}</td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.maturityDate}</td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.duration}</td>
            <td className="text-center px-4 py-4">
              <span className={`font-medium ${(asset.changeBps ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {(asset.changeBps ?? 0) >= 0 ? "+" : ""}
                {asset.changeBps}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  const renderStocksTable = () => (
    <table className="w-full">
      <thead>
        <tr className="bg-[#0a1018] border-b border-[#1e3a5f]">
          <HeaderCell field="name">Stock Name</HeaderCell>
          <HeaderCell field="price" center>
            Price
          </HeaderCell>
          <HeaderCell field="change" center>
            Change
          </HeaderCell>
          <HeaderCell field="volume" center>
            Volume
          </HeaderCell>
          <HeaderCell field="rsi" center>
            RSI
          </HeaderCell>
          <HeaderCell field="vwap" center>
            VWAP
          </HeaderCell>
          <HeaderCell field="signalStrength" center>
            Signal
          </HeaderCell>
          <HeaderCell field="action" center>
            Action
          </HeaderCell>
        </tr>
      </thead>
      <tbody className="divide-y divide-[#1e3a5f]/50">
        {sortedAssets.map((asset) => (
          <tr
            key={asset.id}
            onClick={() => handleRowClick(asset)}
            className={`cursor-pointer transition-colors duration-150 ${selectedRow === asset.id ? "bg-[#14b8a6]/5 border-l-2 border-l-[#14b8a6]" : "hover:bg-[#0f1a24]"}`}
          >
            <td className="px-4 py-4">
              <div>
                <p className="text-[#e2e8f0] font-medium">{asset.name}</p>
                <p className="text-[#6b7a8f] text-sm">{asset.ticker}</p>
              </div>
            </td>
            <td className="text-center text-[#94a3b8] px-4 py-4">₹{asset.price?.toFixed(2)}</td>
            <td className="text-center px-4 py-4">
              <div className="flex flex-col items-center">
                <span className={`font-medium ${(asset.change ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {(asset.change ?? 0) >= 0 ? "+" : ""}
                  {asset.change?.toFixed(2)}
                </span>
                <span className={`text-xs ${(asset.changePercent ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  ({(asset.changePercent ?? 0) >= 0 ? "+" : ""}
                  {asset.changePercent?.toFixed(2)}%)
                </span>
              </div>
            </td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.volume}</td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.rsi?.toFixed(1) ?? "-"}</td>
            <td className="text-center text-[#94a3b8] px-4 py-4">{asset.vwap?.toFixed(2) ?? "-"}</td>
            <td className="text-center px-4 py-4">
              <span className={`font-medium ${(asset.signalStrength ?? 0) >= 0.5 ? "text-emerald-400" : (asset.signalStrength ?? 0) >= 0 ? "text-yellow-400" : "text-red-400"}`}>
                {asset.signalStrength?.toFixed(2) ?? "-"}
              </span>
            </td>
            <td className="text-center px-4 py-4">
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                asset.action === "BUY" ? "bg-emerald-500/20 text-emerald-400" :
                asset.action === "SELL" ? "bg-red-500/20 text-red-400" :
                "bg-gray-500/20 text-gray-400"
              }`}>
                {asset.action ?? "-"}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  const renderForexTable = () => (
    <table className="w-full">
      <thead>
        <tr className="bg-[#0a1018] border-b border-[#1e3a5f]">
          <HeaderCell field="name">Currency Pair</HeaderCell>
          <HeaderCell field="currentPrice" center>
            Current Price
          </HeaderCell>
          <HeaderCell field="previousClose" center>
            Previous Close
          </HeaderCell>
          <HeaderCell field="change" center>
            Change
          </HeaderCell>
          <HeaderCell field="high" center>
            High
          </HeaderCell>
          <HeaderCell field="low" center>
            Low
          </HeaderCell>
        </tr>
      </thead>
      <tbody className="divide-y divide-[#1e3a5f]/50">
        {sortedAssets.map((asset) => (
          <tr
            key={asset.id}
            onClick={() => handleRowClick(asset)}
            className={`cursor-pointer transition-colors duration-150 ${selectedRow === asset.id ? "bg-[#14b8a6]/5 border-l-2 border-l-[#14b8a6]" : "hover:bg-[#0f1a24]"}`}
          >
            <td className="px-4 py-4">
              <div>
                <p className="text-[#e2e8f0] font-medium">{asset.name}</p>
                <p className="text-[#6b7a8f] text-sm">{asset.ticker}</p>
              </div>
            </td>
            <td className="text-center text-[#94a3b8] px-4 py-4">
              {asset.currentPrice?.toFixed(4)}
            </td>
            <td className="text-center text-[#94a3b8] px-4 py-4">
              {asset.previousClose?.toFixed(4)}
            </td>
            <td className="text-center px-4 py-4">
              <div className="flex flex-col items-center">
                <span className={`font-medium ${(asset.change ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {(asset.change ?? 0) >= 0 ? "+" : ""}
                  {asset.change?.toFixed(4)}
                </span>
                <span className={`text-xs ${(asset.changePercent ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  ({(asset.changePercent ?? 0) >= 0 ? "+" : ""}
                  {asset.changePercent?.toFixed(2)}%)
                </span>
              </div>
            </td>
            <td className="text-center text-[#94a3b8] px-4 py-4">
              {asset.high?.toFixed(4) ?? "-"}
            </td>
            <td className="text-center text-[#94a3b8] px-4 py-4">
              {asset.low?.toFixed(4) ?? "-"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  return (
    <div className="overflow-x-auto">
      {assetType === "bonds" && renderBondsTable()}
      {assetType === "stocks" && renderStocksTable()}
      {assetType === "forex" && renderForexTable()}
    </div>
  )
}
