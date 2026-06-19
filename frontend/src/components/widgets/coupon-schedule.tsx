"use client"

import { useState } from "react"
import { DashboardCard } from "../ui/dashboard-card"

const allSchedule = [
  {
    date: "2024-11-15",
    type: "Coupon",
    coupon: "1.25",
    cashFlow: "$12.50",
    principal: "$0.00",
    total: "$12.50",
    status: "Upcoming",
  },
  {
    date: "2025-05-15",
    type: "Coupon",
    coupon: "1.25",
    cashFlow: "$12.50",
    principal: "$0.00",
    total: "$12.50",
    status: "Upcoming",
  },
  {
    date: "2025-11-15",
    type: "Coupon",
    coupon: "1.25",
    cashFlow: "$12.50",
    principal: "$0.00",
    total: "$12.50",
    status: "Upcoming",
  },
  {
    date: "2024-05-15",
    type: "Coupon",
    coupon: "1.25",
    cashFlow: "$12.50",
    principal: "$0.00",
    total: "$12.50",
    status: "Past",
  },
  {
    date: "2045-05-15",
    type: "Coupon+Princ.",
    coupon: "1.25",
    cashFlow: "$12.50",
    principal: "$1,000.00",
    total: "$1,012.50",
    status: "Upcoming",
  },
]

type FilterType = "All" | "Upcoming" | "Past" | "Coupon" | "Principal"

export function CouponSchedule() {
  const [activeFilter, setActiveFilter] = useState<FilterType>("All")
  const [hoveredRow, setHoveredRow] = useState<number | null>(null)

  const filteredSchedule = allSchedule.filter((item) => {
    if (activeFilter === "All") return true
    if (activeFilter === "Upcoming" || activeFilter === "Past") return item.status === activeFilter
    if (activeFilter === "Coupon") return item.type === "Coupon"
    if (activeFilter === "Principal") return item.type.includes("Princ")
    return true
  })

  const filters: FilterType[] = ["All", "Upcoming", "Past", "Coupon", "Principal"]

  return (
    <DashboardCard title="Coupon & Cash Flow Schedule" className="bg-[#143432]">
      <div className="h-full overflow-x-auto">
        <div className="mb-3 flex gap-2">
          {filters.map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`rounded px-3 py-1 text-xs transition-colors ${
                activeFilter === filter
                  ? "bg-[#00c7a5] text-[#0b1623]"
                  : "text-[#8a99ab] hover:bg-[#2a3643] hover:text-[#e1e7ef]"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#2a3643]">
              <th className="pb-2 text-left font-semibold text-[#8a99ab]">Payment Date</th>
              <th className="pb-2 text-left font-semibold text-[#8a99ab]">Type</th>
              <th className="pb-2 text-right font-semibold text-[#8a99ab]">Coupon %</th>
              <th className="pb-2 text-right font-semibold text-[#8a99ab]">Cash Flow</th>
              <th className="pb-2 text-right font-semibold text-[#8a99ab]">Principal</th>
              <th className="pb-2 text-right font-semibold text-[#8a99ab]">Total Payment</th>
              <th className="pb-2 text-left font-semibold text-[#8a99ab]">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredSchedule.map((item, index) => (
              <tr
                key={index}
                onMouseEnter={() => setHoveredRow(index)}
                onMouseLeave={() => setHoveredRow(null)}
                className={`border-b border-[#2a3643] transition-colors ${hoveredRow === index ? "bg-[#1a2530]" : ""}`}
              >
                <td className="py-2 text-[#e1e7ef]">{item.date}</td>
                <td className="py-2 text-[#e1e7ef]">{item.type}</td>
                <td className="py-2 text-right text-[#e1e7ef]">{item.coupon}</td>
                <td className="py-2 text-right text-[#e1e7ef]">{item.cashFlow}</td>
                <td className="py-2 text-right text-[#e1e7ef]">{item.principal}</td>
                <td className="py-2 text-right font-semibold text-[#00c7a5]">{item.total}</td>
                <td className={`py-2 ${item.status === "Upcoming" ? "text-[#00c7a5]" : "text-[#8a99ab]"}`}>
                  {item.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardCard>
  )
}
