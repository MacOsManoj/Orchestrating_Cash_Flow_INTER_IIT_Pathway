import type React from "react"
import { cn } from "@/lib/utils"

interface DashboardCardProps {
  children: React.ReactNode
  className?: string
}

export function DashboardCard({ children, className }: DashboardCardProps) {
  return <div className={cn("bg-card border border-border rounded-lg p-6 h-full", className)}>{children}</div>
}
