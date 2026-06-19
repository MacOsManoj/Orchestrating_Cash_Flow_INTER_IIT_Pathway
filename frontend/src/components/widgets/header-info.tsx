"use client"

import { DashboardCard } from "../ui/dashboard-card"

export function HeaderInfo() {
  return (
    <DashboardCard className="bg-[#143432]">
      <div className="flex h-full flex-col justify-between">
        <div>
          <h1 className="mb-2 text-2xl font-bold text-[#00c7a5]">US Treasury Bond - 2.5% 2045 (912810SL1)</h1>
          <p className="text-xs text-[#8a99ab]">CUSIP: 912810SL1 / ISIN: US912810SL10 / FIGI: BBG000B9XRY1</p>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
          <div>
            <p className="text-xs text-[#8a99ab]">Last Price</p>
            <p className="text-xl font-bold text-[#e1e7ef]">98.75</p>
            <p className="text-xs text-[#00c7a5]">+0.12%</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Yield (YTM)</p>
            <p className="text-xl font-bold text-[#e1e7ef]">2.85%</p>
            <p className="text-xs text-[#e00618]">-0.05%</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Maturity Date</p>
            <p className="text-xl font-bold text-[#e1e7ef]">2045-05-15</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Coupon Rate</p>
            <p className="text-xl font-bold text-[#e1e7ef]">2.50%</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Frequency</p>
            <p className="text-xl font-bold text-[#e1e7ef]">Semi-Annual</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Day Count</p>
            <p className="text-xl font-bold text-[#e1e7ef]">30/360</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
          <div>
            <p className="text-xs text-[#8a99ab]">Issue Date</p>
            <p className="text-sm text-[#e1e7ef]">2015-05-15</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Next Coupon</p>
            <p className="text-sm text-[#e1e7ef]">2024-11-15</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Accrued Interest</p>
            <p className="text-sm text-[#e1e7ef]">$0.83</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Credit Rating</p>
            <p className="text-sm text-[#e1e7ef]">AAA</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Min. Increment</p>
            <p className="text-sm text-[#e1e7ef]">$1,000</p>
          </div>
          <div>
            <p className="text-xs text-[#8a99ab]">Settlement</p>
            <p className="text-sm text-[#e1e7ef]">T+2</p>
          </div>
        </div>
      </div>
    </DashboardCard>
  )
}
