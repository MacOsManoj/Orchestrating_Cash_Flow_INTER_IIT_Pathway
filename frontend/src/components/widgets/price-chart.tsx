"use client"

import { useState } from "react"
import { DashboardCard } from "../ui/dashboard-card"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const dataByPeriod = {
  "1W": [
    { date: "Feb 18", price: 98.2 },
    { date: "Feb 19", price: 98.5 },
    { date: "Feb 20", price: 98.1 },
    { date: "Feb 21", price: 98.75 },
    { date: "Feb 22", price: 98.6 },
  ],
  "1M": [
    { date: "Jan 24", price: 97.5 },
    { date: "Feb 1", price: 98.0 },
    { date: "Feb 8", price: 97.8 },
    { date: "Feb 15", price: 98.5 },
    { date: "Feb 22", price: 98.75 },
  ],
  "3M": [
    { date: "Nov 23", price: 96.5 },
    { date: "Dec 23", price: 97.2 },
    { date: "Jan 24", price: 97.5 },
    { date: "Feb 24", price: 98.75 },
  ],
  YTD: [
    { date: "Jan 1", price: 97.0 },
    { date: "Jan 15", price: 97.5 },
    { date: "Feb 1", price: 98.0 },
    { date: "Feb 15", price: 98.5 },
    { date: "Feb 24", price: 98.75 },
  ],
  "1Y": [
    { date: "Mar 23", price: 95.0 },
    { date: "Jun 23", price: 96.5 },
    { date: "Sep 23", price: 97.0 },
    { date: "Dec 23", price: 97.2 },
    { date: "Feb 24", price: 98.75 },
  ],
  MAX: [
    { date: "2015", price: 92.0 },
    { date: "2017", price: 94.5 },
    { date: "2019", price: 96.0 },
    { date: "2021", price: 95.5 },
    { date: "2023", price: 97.0 },
    { date: "2024", price: 98.75 },
  ],
}

export function PriceChart() {
  const [activePeriod, setActivePeriod] = useState<keyof typeof dataByPeriod>("1M")
  const data = dataByPeriod[activePeriod]

  return (
    <DashboardCard
      title="Price Chart"
      className="bg-[#143432]"
      headerAction={
        <div className="flex gap-2 text-xs">
          {(Object.keys(dataByPeriod) as Array<keyof typeof dataByPeriod>).map((period) => (
            <button
              key={period}
              onClick={() => setActivePeriod(period)}
              className={`rounded px-2 py-1 transition-colors ${
                activePeriod === period
                  ? "bg-[#00c7a5] text-[#0b1623]"
                  : "text-[#8a99ab] hover:bg-[#2a3643] hover:text-[#e1e7ef]"
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      }
    >
      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00c7a5" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#00c7a5" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a3643" />
            <XAxis dataKey="date" stroke="#8a99ab" style={{ fontSize: "12px" }} />
            <YAxis stroke="#8a99ab" style={{ fontSize: "12px" }} domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#161e27",
                border: "1px solid #2a3643",
                borderRadius: "8px",
                color: "#e1e7ef",
              }}
              formatter={(value: number) => [`$${value.toFixed(2)}`, "Price"]}
            />
            <Area type="monotone" dataKey="price" stroke="#00c7a5" strokeWidth={2} fill="url(#colorPrice)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </DashboardCard>
  )
}
