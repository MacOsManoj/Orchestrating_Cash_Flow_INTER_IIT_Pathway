"use client";

import { DashboardCard } from "../ui/dashboard-card";

export function Summary() {
  return (
    <DashboardCard title="Summary" className="bg-[#143432]">
      <div className="h-full overflow-y-auto">
        <p className="text-xs leading-relaxed text-[#8a99ab]">
          This bond shows stable pricing with minimal recent volatility. Its
          yield is slightly above the benchmark, reflecting a positive spread.
          Key risk factors include duration sensitivity to interest rate
          changes.
        </p>
      </div>
    </DashboardCard>
  );
}
