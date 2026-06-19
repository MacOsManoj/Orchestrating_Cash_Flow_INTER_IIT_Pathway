"use client";

import { motion } from "framer-motion";
import type { ComponentSize } from "../CanvasLayout";

interface SentimentAnalysisCardProps {
  sentimentScore?: string; // e.g. "0.32 (neutral)" or "bearish (-0.45)"
  reasoning?: string;
}

interface SentimentAnalysisCardComponent
  extends React.FC<SentimentAnalysisCardProps> {
  canvasSize?: ComponentSize;
}

export const SentimentAnalysisCard: SentimentAnalysisCardComponent = ({
  sentimentScore,
  reasoning,
}) => {
  const hasScore = !!sentimentScore && sentimentScore.trim() !== "";
  const hasReasoning = !!reasoning && reasoning.trim() !== "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="rounded-lg bg-gradient-to-br from-slate-900 to-slate-950 
                 border border-slate-800 p-2 sm:p-2.5 md:p-3 w-full h-full
                 flex flex-col"
    >
      {/* Title - compact */}
      <h3 className="text-white text-xs sm:text-sm md:text-base font-bold mb-2 sm:mb-2.5 md:mb-3 leading-tight">
        Sentiment Analysis
      </h3>

      <div className="space-y-1.5 sm:space-y-2 md:space-y-3 flex-1 overflow-y-auto">
        {/* Sentiment Score */}
        {hasScore && (
          <div className="flex flex-col gap-0.5 sm:gap-1">
            <h4 className="text-slate-400 text-[8px] sm:text-[9px] md:text-xs font-medium uppercase tracking-wider leading-tight">
              Sentiment score
            </h4>
            <p className="text-white text-sm sm:text-base md:text-lg font-semibold leading-tight break-words">
              {sentimentScore}
            </p>
          </div>
        )}

        {/* Reasoning */}
        {hasReasoning && (
          <div className="flex flex-col gap-0.5 sm:gap-1">
            <h4 className="text-slate-400 text-[8px] sm:text-[9px] md:text-xs font-medium uppercase tracking-wider leading-tight">
              Reasoning
            </h4>
            <p className="text-slate-300 text-[10px] sm:text-xs md:text-sm leading-snug break-words">
              {reasoning}
            </p>
          </div>
        )}

        {!hasScore && !hasReasoning && (
          <p className="text-slate-500 text-[10px] sm:text-xs">
            No sentiment data available.
          </p>
        )}
      </div>
    </motion.div>
  );
};

SentimentAnalysisCard.canvasSize = "medium";