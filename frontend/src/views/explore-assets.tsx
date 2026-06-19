"use client";

import { useState, useMemo, useEffect } from "react";
import { Search, AlertCircle } from "lucide-react";
import { MarketIndexCard } from "../components/explore-assets/market-index-card";
import { FilterDropdown } from "../components/explore-assets/filter-dropdown";
import { AssetTable } from "../components/explore-assets/asset-table";
import {
  AssetTableSkeleton,
  MarketIndexSkeleton,
} from "../components/explore-assets/asset-skeleton";
import {
  assetClassOptions,
  stockRegionOptions,
  stockSectorOptions,
  bondRegionOptions,
  bondSectorOptions,
  forexRegionOptions,
} from "../components/explore-assets/data/assets-data";
import type {
  Asset,
  MarketIndex,
} from "../components/explore-assets/data/types";
import {
  useMarketIndices,
  useAssetsByClass,
} from "../queries/assets_queries";

export function ExploreAssets() {
  const [searchQuery, setSearchQuery] = useState("");
  const [assetClass, setAssetClass] = useState<"bonds" | "stocks" | "forex">("stocks");
  const [region, setRegion] = useState("all");
  const [sector, setSector] = useState("all");
  const [selectedIndex, setSelectedIndex] = useState<MarketIndex | null>(null);

  // API Queries
  const {
    data: marketIndices = [],
    isLoading: isLoadingIndices,
  } = useMarketIndices();

  const {
    data: assets = [],
    isLoading: isLoadingAssets,
    error: assetsError,
  } = useAssetsByClass(assetClass);

  // Get filter options based on asset class
  const getRegionOptions = () => {
    switch (assetClass) {
      case "stocks":
        return stockRegionOptions;
      case "bonds":
        return bondRegionOptions;
      case "forex":
        return forexRegionOptions;
      default:
        return stockRegionOptions;
    }
  };

  const getSectorOptions = () => {
    switch (assetClass) {
      case "stocks":
        return stockSectorOptions;
      case "bonds":
        return bondSectorOptions;
      case "forex":
        return []; // Forex doesn't have sector filter
      default:
        return stockSectorOptions;
    }
  };

  // Reset filters when asset class changes
  const handleAssetClassChange = (value: string) => {
    setAssetClass(value as "bonds" | "stocks" | "forex");
    setRegion("all");
    setSector("all");
    setSearchQuery("");
  };

  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const matchesSearch =
        asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        asset.ticker.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesRegion = region === "all" || asset.region === region;
      const matchesSector = sector === "all" || asset.sector === sector;

      return matchesSearch && matchesRegion && matchesSector;
    });
  }, [assets, searchQuery, region, sector]);

  const handleIndexClick = (index: MarketIndex) => {
    setSelectedIndex(selectedIndex?.id === index.id ? null : index);
  };

  const handleTrade = (asset: Asset) => {
    alert(`Opening trade dialog for ${asset.name} (${asset.ticker})`);
  };

  const clearFilters = () => {
    setSearchQuery("");
    setRegion("all");
    setSector("all");
  };

  const hasActiveFilters = searchQuery || region !== "all" || sector !== "all";

  const regionOptions = getRegionOptions();
  const sectorOptions = getSectorOptions();

  return (
    <div className="min-h-screen bg-background text-primary flex">
      <div className="flex-1 flex flex-col">
        <main className="flex-1 p-8 overflow-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2 text-primary">
              Explore Assets
            </h1>
            <p className="text-[#6b7a8f]">
              Discover investment opportunities tailored for your firm.
            </p>
          </div>

          {/* Search Bar */}
          <div className="relative max-w-2xl mx-auto mb-6">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#6b7a8f]" />
            <input
              type="text"
              placeholder="Search by asset name, ticker, ISIN..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0f1a24] border border-[#1e3a5f] rounded-full py-3 pl-12 pr-4 text-[#e2e8f0] placeholder-[#6b7a8f] focus:outline-none focus:ring-2 focus:ring-[#14b8a6]/50 focus:border-[#14b8a6]/50 transition-all"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
            <div className="flex gap-3 flex-wrap">
              <FilterDropdown
                label="Asset Class"
                options={assetClassOptions}
                value={assetClass}
                onChange={handleAssetClassChange}
              />
              <FilterDropdown
                label={assetClass === "forex" ? "Pair Type" : "Region"}
                options={regionOptions}
                value={region}
                onChange={setRegion}
              />
              {sectorOptions.length > 0 && (
                <FilterDropdown
                  label="Sector"
                  options={sectorOptions}
                  value={sector}
                  onChange={setSector}
                />
              )}

              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-[#14b8a6] hover:text-[#14b8a6]/80 hover:underline transition-colors"
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>

          {/* Key Market Indices */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold mb-4 text-[#e2e8f0]">
              Key Market Indices
            </h2>
            {isLoadingIndices ? (
              <MarketIndexSkeleton />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {marketIndices.map((index) => (
                  <MarketIndexCard
                    key={index.id}
                    index={index}
                    onClick={handleIndexClick}
                  />
                ))}
              </div>
            )}
            {selectedIndex && (
              <div className="mt-4 p-4 bg-[#0f1a24] border border-[#14b8a6]/30 rounded-lg animate-in fade-in slide-in-from-top-2 duration-200">
                <p className="text-[#e2e8f0]">
                  Selected:{" "}
                  <span className="font-bold">{selectedIndex.name}</span> -
                  Current value:{" "}
                  <span className="font-mono">
                    {selectedIndex.value.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                    })}
                  </span>
                </p>
              </div>
            )}
          </div>

          {/* Assets Table */}
          <div className="bg-[#0a1018] rounded-lg border border-[#1e3a5f] overflow-hidden">
            {isLoadingAssets ? (
              <AssetTableSkeleton rows={10} assetType={assetClass} />
            ) : assetsError ? (
              <div className="p-8 text-center">
                <div className="flex flex-col items-center gap-3">
                  <AlertCircle className="w-8 h-8 text-red-400" />
                  <p className="text-red-400">
                    Failed to load assets. Please try again later.
                  </p>
                  <button
                    onClick={() => window.location.reload()}
                    className="mt-2 text-[#14b8a6] hover:underline"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ) : (
              <>
                <AssetTable
                  assets={filteredAssets}
                  assetType={assetClass}
                />
                {filteredAssets.length === 0 && (
                  <div className="p-8 text-center text-[#6b7a8f]">
                    <p>
                      No {assetClass} match your current filters.
                    </p>
                    <button
                      onClick={clearFilters}
                      className="mt-2 text-[#14b8a6] hover:underline"
                    >
                      Clear filters
                    </button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Results count */}
          {!isLoadingAssets && !assetsError && (
            <div className="mt-4 text-sm text-[#6b7a8f]">
              Showing {filteredAssets.length} of {assets.length} {assetClass}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
