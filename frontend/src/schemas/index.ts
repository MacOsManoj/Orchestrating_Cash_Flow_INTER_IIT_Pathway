/**
 * Central export file for all asset schemas
 * Provides unified access to all schema definitions
 */

export * from './stocks'
export * from './bonds'
export * from './options'
export type {
  CommodityIdentifier,
  CommodityPrice,
  CommodityHoldings,
  CommodityKeyStats,
  CommodityChart,
  CommodityNews,
  RiskWarning,
  RiskTracking,
  CommodityCorrelation,
  FullCommodityData,
  CommodityType
} from './commodities'
export { COMMODITY_TYPES, COMMODITY_SYMBOLS } from './commodities'
export * from './fx'

/**
 * JSON Schema file references for runtime validation
 */
export const jsonSchemas = {
  stocks: 'stocks.schema.json',
  bonds: 'bonds.schema.json',
  options: 'options.schema.json',
  commodities: 'commodities.schema.json',
  fx: 'fx.schema.json'
} as const

/**
 * Asset class types
 */
export type AssetClass = 'stocks' | 'bonds' | 'options' | 'commodities' | 'fx'

/**
 * Union type for all possible asset data structures
 */
import type { FullStockData } from './stocks'
import type { FullBondData } from './bonds'
import type { FullOptionData } from './options'
import type { FullCommodityData } from './commodities'
import type { FullFXData } from './fx'

export type AssetData = 
  | FullStockData 
  | FullBondData 
  | FullOptionData 
  | FullCommodityData 
  | FullFXData

/**
 * Mapping of asset class to its data type
 * Useful for type-safe asset handling
 */
export const assetClassMap = {
  stocks: 'FullStockData',
  bonds: 'FullBondData',
  options: 'FullOptionData',
  commodities: 'FullCommodityData',
  fx: 'FullFXData'
} as const
