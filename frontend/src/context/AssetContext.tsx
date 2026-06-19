import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { Asset } from '@/components/explore-assets/data/types';

interface AssetContextType {
  selectedAsset: Asset | null;
  setSelectedAsset: (asset: Asset | null) => void;
  navigateToAsset: ((asset: Asset) => void) | null;
  setNavigateToAsset: (fn: ((asset: Asset) => void) | null) => void;
  // Store assets by tab ID for multi-tab support
  assetsByTabId: Record<string, Asset>;
  setAssetForTab: (tabId: string, asset: Asset) => void;
  getAssetForTab: (tabId: string) => Asset | null;
  currentTabId: string | null;
  setCurrentTabId: (tabId: string | null) => void;
}

const AssetContext = createContext<AssetContextType | undefined>(undefined);

export function AssetProvider({ children }: { children: ReactNode }) {
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [navigateToAsset, setNavigateToAssetFn] = useState<((asset: Asset) => void) | null>(null);
  const [assetsByTabId, setAssetsByTabId] = useState<Record<string, Asset>>({});
  const [currentTabId, setCurrentTabId] = useState<string | null>(null);

  const setNavigateToAsset = useCallback((fn: ((asset: Asset) => void) | null) => {
    setNavigateToAssetFn(() => fn);
  }, []);

  const setAssetForTab = useCallback((tabId: string, asset: Asset) => {
    setAssetsByTabId(prev => ({ ...prev, [tabId]: asset }));
  }, []);

  const getAssetForTab = useCallback((tabId: string): Asset | null => {
    return assetsByTabId[tabId] || null;
  }, [assetsByTabId]);

  return (
    <AssetContext.Provider 
      value={{ 
        selectedAsset, 
        setSelectedAsset,
        navigateToAsset,
        setNavigateToAsset,
        assetsByTabId,
        setAssetForTab,
        getAssetForTab,
        currentTabId,
        setCurrentTabId,
      }}
    >
      {children}
    </AssetContext.Provider>
  );
}

export function useAsset() {
  const context = useContext(AssetContext);
  if (context === undefined) {
    throw new Error('useAsset must be used within an AssetProvider');
  }
  return context;
}
