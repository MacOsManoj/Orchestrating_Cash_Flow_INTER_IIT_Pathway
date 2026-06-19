"use client";

import React from "react";
import { motion } from "framer-motion";
import type { ComponentSize } from "../CanvasLayout";

interface BondPricingCardProps {
  // schema fields (will usually be present)
  lastPrice?: number;
  cleanPrice?: number;
  accruedInterest?: number;

  // optional extras – safe to ignore if not provided
  priceChange?: number;
  bid?: number;
  ask?: number;
  bidAskSpread?: number;
  dirtyPrice?: number;
}

interface BondPricingCardComponent extends React.FC<BondPricingCardProps> {
  canvasSize?: ComponentSize;
}

function formatNumber(value?: number): string | null {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return null;
  }
  return value.toFixed(2);
}

export const BondPricingCard: BondPricingCardComponent = ({
  lastPrice,
  cleanPrice,
  accruedInterest,
  priceChange,
  bid,
  ask,
  bidAskSpread,
  dirtyPrice,
}) => {
  const headline = formatNumber(lastPrice);

  const mainRows = [
    { label: "Clean price", value: formatNumber(cleanPrice) },
    { label: "Accrued interest", value: formatNumber(accruedInterest) },
  ].filter((row) => row.value !== null);

  const extraRows = [
    { label: "Daily change", value: formatNumber(priceChange) },
    { label: "Bid", value: formatNumber(bid) },
    { label: "Ask", value: formatNumber(ask) },
    { label: "Bid/ask spread", value: formatNumber(bidAskSpread) },
    { label: "Dirty price", value: formatNumber(dirtyPrice) },
  ].filter((row) => row.value !== null);

  const hasAnyDetail = mainRows.length > 0 || extraRows.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full h-full rounded-lg bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 p-2 sm:p-2.5 md:p-3 flex flex-col"
    >
      {/* Header / title */}
      <div className="mb-2 sm:mb-2.5 md:mb-3">
        <h3 className="text-white text-xs sm:text-sm md:text-base font-bold leading-tight">
          Bond Pricing
        </h3>
      </div>

      {/* Last price big number */}
      <div className="mb-2 sm:mb-2.5 md:mb-3">
        <p className="text-slate-400 text-[8px] sm:text-[9px] md:text-xs uppercase tracking-wider leading-tight">
          Last price
        </p>
        <p className="text-white text-lg sm:text-xl md:text-2xl font-semibold leading-tight mt-0.5">
          {headline ?? "—"}
        </p>
      </div>

      {/* Details */}
      {hasAnyDetail ? (
        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-1.5 sm:gap-2 md:gap-2.5 text-[10px] sm:text-xs md:text-sm">
          {mainRows.map((row, idx) => (
            <div key={`main-${idx}`} className="flex flex-col">
              <span className="text-slate-400 text-[8px] sm:text-[9px] md:text-xs uppercase tracking-wider leading-tight">
                {row.label}
              </span>
              <span className="text-slate-100 font-medium leading-tight mt-0.5">
                {row.value}
              </span>
            </div>
          ))}

          {extraRows.map((row, idx) => (
            <div key={`extra-${idx}`} className="flex flex-col">
              <span className="text-slate-400 text-[8px] sm:text-[9px] md:text-xs uppercase tracking-wider leading-tight">
                {row.label}
              </span>
              <span className="text-slate-100 font-medium leading-tight mt-0.5">
                {row.value}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-slate-500 text-[10px] sm:text-xs">
          No pricing details available.
        </p>
      )}
    </motion.div>
  );
};

BondPricingCard.canvasSize = "small";