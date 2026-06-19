"use client"

import { motion } from "framer-motion"
import type { ComponentSize } from "../CanvasLayout"

interface BondTermsCardProps {
  bondName?: string
  couponRate?: string
  maturityDate?: string
  rating?: string

  // Optional extras (only shown if provided)
  couponFrequency?: string
  nextCouponDate?: string
  faceValue?: string
  settlementType?: string
}

interface BondTermsCardComponent extends React.FC<BondTermsCardProps> {
  canvasSize?: ComponentSize
}

export const BondTermsCard: BondTermsCardComponent = ({
  bondName,
  couponRate,
  maturityDate,
  rating,
  couponFrequency,
  nextCouponDate,
  faceValue,
  settlementType,
}) => {
  const rowsLeft = [
    { label: "Coupon rate", value: couponRate },
    { label: "Coupon frequency", value: couponFrequency },
    { label: "Settlement type", value: settlementType },
    { label: "Rating", value: rating },
  ].filter(r => r.value && r.value.trim() !== "")

  const rowsRight = [
    { label: "Maturity date", value: maturityDate },
    { label: "Next coupon date", value: nextCouponDate },
    { label: "Face value", value: faceValue },
  ].filter(r => r.value && r.value.trim() !== "")

  const hasAnyData = rowsLeft.length > 0 || rowsRight.length > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="
        rounded-lg bg-gradient-to-br from-slate-900 to-slate-950
        border border-slate-800 p-2 sm:p-2.5 md:p-3 w-full h-full
        flex flex-col
      "
    >
      {/* Bond Name */}
      <div className="mb-2 sm:mb-2.5 md:mb-3">
        <h3 className="text-white text-xs sm:text-sm md:text-base font-bold leading-tight">
          {bondName || "Bond Terms"}
        </h3>
      </div>

      {hasAnyData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 sm:gap-2 flex-1">
          {/* Left Column */}
          <div className="space-y-1 sm:space-y-1.5">
            {rowsLeft.map((row, i) => (
              <div key={`left-${i}`} className="flex flex-col">
                <span className="text-slate-400 text-[8px] sm:text-[9px] md:text-xs uppercase tracking-wider">
                  {row.label}
                </span>
                <span className="text-white text-xs sm:text-sm md:text-base font-medium mt-0.5">
                  {row.value}
                </span>
              </div>
            ))}
          </div>

          {/* Right Column */}
          <div className="space-y-1 sm:space-y-1.5">
            {rowsRight.map((row, i) => (
              <div key={`right-${i}`} className="flex flex-col">
                <span className="text-slate-400 text-[8px] sm:text-[9px] md:text-xs uppercase tracking-wider">
                  {row.label}
                </span>
                <span className="text-white text-xs sm:text-sm md:text-base font-medium mt-0.5">
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-slate-500 text-[10px] sm:text-xs">
          No bond details available.
        </p>
      )}
    </motion.div>
  )
}

BondTermsCard.canvasSize = "small"
