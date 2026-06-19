"use client"

import type React from "react"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface DashboardCardProps {
  title?: string
  children: React.ReactNode
  className?: string
  headerAction?: React.ReactNode
}

export function DashboardCard({ title, children, className, headerAction }: DashboardCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("h-full rounded-lg border border-[#2a3643] bg-[#161e27] p-4 shadow-lg", className)}
    >
      {title && (
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#e1e7ef]">{title}</h3>
          {headerAction}
        </div>
      )}
      <div className="h-[calc(100%-2rem)]">{children}</div>
    </motion.div>
  )
}
