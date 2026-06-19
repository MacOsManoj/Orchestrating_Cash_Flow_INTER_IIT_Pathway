"use client"

import { DashboardCard } from "../ui/dashboard-card"

export function MarketUpdates() {
  return (
    <DashboardCard title="Market Updates" className="bg-[#143432]">
      <div className="h-full space-y-3 overflow-y-auto">
        <div>
          <p className="mb-1 text-xs font-semibold text-[#e1e7ef]">Yield curve inversion deepens:</p>
          <p className="text-xs leading-relaxed text-[#8a99ab]">
            Recession fears impact short-term bond outlook. Central bank maintains dovish stance.
          </p>
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold text-[#e1e7ef]">Long-term bond yields rising:</p>
          <p className="text-xs leading-relaxed text-[#8a99ab]">
            Inflation expectations drive long-term rates higher, creating volatility.
          </p>
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold text-[#e1e7ef]">Strong employment report:</p>
          <p className="text-xs leading-relaxed text-[#8a99ab]">
            Potential for future rate hikes creates volatility in bond markets.
          </p>
        </div>
      </div>
    </DashboardCard>
  )
}
