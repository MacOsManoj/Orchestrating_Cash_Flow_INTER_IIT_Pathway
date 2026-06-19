"use client";

interface AssetTableSkeletonProps {
  rows?: number;
  assetType?: string;
}

export function AssetTableSkeleton({
  rows = 8,
  assetType = "all",
}: AssetTableSkeletonProps) {
  const getColumnCount = () => {
    switch (assetType) {
      case "bonds":
        return 8;
      case "stocks":
        return 8;
      case "etfs":
        return 8;
      case "commodities":
        return 7;
      default:
        return 7;
    }
  };

  const columns = getColumnCount();

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-[#0a1018] border-b border-[#1e3a5f]">
            {Array.from({ length: columns }).map((_, i) => (
              <th
                key={i}
                className="text-left text-[#6b7a8f] text-xs font-medium uppercase tracking-wider px-4 py-3"
              >
                <div className="h-4 bg-[#1e3a5f] rounded animate-pulse w-20" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#1e3a5f]/50">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-[#0f1a24]">
              {/* Name column - wider */}
              <td className="px-4 py-4">
                <div className="space-y-2">
                  <div className="h-4 bg-[#1e3a5f] rounded animate-pulse w-32" />
                  <div className="h-3 bg-[#1e3a5f]/60 rounded animate-pulse w-16" />
                </div>
              </td>
              {/* Other columns */}
              {Array.from({ length: columns - 1 }).map((_, colIndex) => (
                <td key={colIndex} className="text-center px-4 py-4">
                  <div className="h-4 bg-[#1e3a5f] rounded animate-pulse w-16 mx-auto" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MarketIndexSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          key={index}
          className="bg-[#0a1018] border border-[#1e3a5f] rounded-lg p-4 animate-pulse"
        >
          <div className="flex justify-between items-start mb-3">
            <div className="h-4 bg-[#1e3a5f] rounded w-20" />
            <div className="h-6 bg-[#1e3a5f] rounded w-16" />
          </div>
          <div className="h-8 bg-[#1e3a5f] rounded w-28 mb-2" />
          <div className="flex items-center gap-2">
            <div className="h-4 bg-[#1e3a5f] rounded w-12" />
            <div className="h-4 bg-[#1e3a5f] rounded w-10" />
          </div>
          <div className="mt-3 h-12 bg-[#1e3a5f]/50 rounded" />
        </div>
      ))}
    </div>
  );
}

export function FiltersSkeleton() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-4 mb-8 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-12 h-6 bg-[#1e3a5f] rounded-full" />
        <div className="h-4 bg-[#1e3a5f] rounded w-36" />
      </div>
      <div className="flex gap-3 flex-wrap">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 bg-[#1e3a5f] rounded-lg w-28" />
        ))}
      </div>
    </div>
  );
}
