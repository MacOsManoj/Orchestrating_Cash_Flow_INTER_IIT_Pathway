"use client"

import { DashboardCard } from "../ui/dashboard-card"

export function ImpactOnPortfolio() {
  return (
    <DashboardCard title="Impact on Portfolio" className="bg-[#143432]">
      <div className="flex h-full flex-col justify-center">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-xs text-[#8a99ab]">Allocation</span>
          <span className="text-xs text-[#8a99ab]">Portfolio Yield</span>
        </div>
        <div className="mb-4 flex items-baseline justify-between">
          <span className="text-3xl font-bold text-[#00c7a5]">1.25%</span>
          <span className="text-xl font-semibold text-[#00c7a5]">+0.03%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[#145b5b]">
          <div className="h-full w-[12.5%] bg-[#00c7a5]" />
        </div>
      </div>
    </DashboardCard>
  )
}
