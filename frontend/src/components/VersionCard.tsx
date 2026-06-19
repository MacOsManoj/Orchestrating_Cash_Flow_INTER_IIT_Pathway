// src/components/VersionCard.tsx
import React from "react";
import type { Version } from "../api/versions";

interface VersionCardProps {
  version: Version;
  isActive: boolean;
  onClick: () => void;
}

export const VersionCard: React.FC<VersionCardProps> = ({
  version,
  isActive,
  onClick,
}) => {
  const componentCount = (version.components || []).length;

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-all flex items-center justify-between ${
        isActive
          ? "bg-teal-700/10 border-teal-600"
          : "bg-[#0a0e14] border-gray-800 hover:border-gray-700"
      }`}
    >
      {/* Version number badge */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded ${
            isActive ? 'bg-teal-600' : 'bg-gray-700'
          }`}
        >
          Version {version.versionNumber}
        </span>
      </div>

      {/* Prompt preview */}


      <div className="text-xs text-gray-400">
        <span>{componentCount} component(s)</span>
      </div>
    </button>
  );
};
