import { useQuery } from "@tanstack/react-query";
import type { Asset, MarketIndex } from "../components/explore-assets/data/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

// ============================================================================
// TYPES
// ============================================================================

// Forex API Response Types
export interface ForexPairSummary {
  pair: string;
  current_price: number;
  previous_close: number;
  price_change_1d: number;
  price_change_pct_1d: number;
  high_1d?: number;
  low_1d?: number;
}

export interface ForexPairsResponse {
  pairs: ForexPairSummary[];
  timestamp: string;
}

// Bonds API Response Types
export interface BondSummary {
  isin: string;
  bond_name: string;
  coupon_rate: number | null;
  maturity_date: string;
  last_price: number;
}

// ============================================================================
// DUMMY DATA
// ============================================================================

// Dummy market indices data
export const DUMMY_MARKET_INDICES: MarketIndex[] = [
  {
    id: "1",
    name: "S&P 500",
    value: 5431.6,
    change: 21.43,
    changePercent: 0.4,
    trend: "up",
    chartData: [20, 25, 22, 28, 26, 30, 28, 32, 35, 33, 38, 40],
  },
  {
    id: "2",
    name: "FTSE 100",
    value: 8146.86,
    change: -15.58,
    changePercent: -0.19,
    trend: "down",
    chartData: [40, 38, 42, 35, 38, 32, 35, 30, 33, 28, 30, 25],
  },
  {
    id: "3",
    name: "NASDAQ",
    value: 17667.56,
    change: 59.12,
    changePercent: 0.34,
    trend: "up",
    chartData: [15, 18, 16, 22, 20, 25, 23, 28, 26, 30, 32, 35],
  },
  {
    id: "4",
    name: "NIKKEI 225",
    value: 38720.47,
    change: -65.66,
    changePercent: -0.17,
    trend: "down",
    chartData: [45, 42, 44, 40, 42, 38, 40, 36, 38, 34, 36, 32],
  },
];

// Stock Data (static for now)
export const STOCK_DATA: Record<string, string> = {
  "Reliance Industries Ltd": "738561",
  "HDFC Bank Ltd": "341249",
  "ICICI Bank Ltd": "1270529",
  "Infosys Ltd": "1594",
  "State Bank of India": "617473",
  "Tata Consultancy Services Ltd": "2953217",
  "Bharti Airtel Ltd": "2714625",
  "ITC Ltd": "424961",
  "Larsen & Toubro Ltd": "2933761",
  "Kotak Mahindra Bank Ltd": "492033",
  "Hindustan Unilever Ltd": "356865",
  "Axis Bank Ltd": "1510401",
  "Bajaj Finance Ltd": "81153",
  "Adani Enterprises Ltd": "6401",
  "Adani Ports and SEZ Ltd": "3861249",
  "Sun Pharmaceutical Industries Ltd": "857857",
  "Maruti Suzuki India Ltd": "2815745",
  "Mahindra & Mahindra Ltd": "519937",
  "UltraTech Cement Ltd": "2952193",
  "Tata Steel Ltd": "895745",
  "Nestle India Ltd": "4598529",
  "Wipro Ltd": "969473",
  "Tech Mahindra Ltd": "3465729",
  "JSW Steel Ltd": "3001089",
  "Power Grid Corporation of India Ltd": "3834113",
  "NTPC Ltd": "2977281",
  "Coal India Ltd": "5215745",
  "Tata Motors Ltd": "884737",
  "Tata Consumer Products Ltd": "878593",
  "Grasim Industries Ltd": "315393",
  "Bajaj Finserv Ltd": "4268801",
  "HCL Technologies Ltd": "1152769",
  "Asian Paints Ltd": "60417",
  "HDFC Life Insurance Company Ltd": "119553",
  "SBI Life Insurance Company Ltd": "5582849",
  "Divi's Laboratories Ltd": "2800641",
  "Cipla Ltd": "177665",
  "Dr. Reddy's Laboratories Ltd": "225537",
  "Titan Company Ltd": "90113",
  "Britannia Industries Ltd": "31873",
  "Eicher Motors Ltd": "232961",
  "Tata Power Company Ltd": "877057",
  "Indian Oil Corporation Ltd": "415745",
  "Hindalco Industries Ltd": "348929",
  "UPL Ltd": "2883073",
  "Shree Cement Ltd": "2810625",
  "Bharat Petroleum Corporation Ltd": "134657",
  "Hero MotoCorp Ltd": "345089",
  "ONGC Ltd": "633601",
  "Zomato Ltd": "12672001",
  "Adani Green Energy Ltd": "1207553",
  "Adani Transmission Ltd": "3609601",
  "Ambuja Cements Ltd": "325121",
  "Dabur India Ltd": "197633",
  "Pidilite Industries Ltd": "681985",
  "SBI Cards and Payment Services Ltd": "17996737",
  "ICICI Lombard General Insurance Ltd": "5572097",
  "ICICI Prudential Life Insurance Ltd": "5573121",
  "DLF Ltd": "3771393",
  "Havells India Ltd": "2513665",
  "Berger Paints India Ltd": "160001",
  "Godrej Consumer Products Ltd": "2585345",
  "Colgate Palmolive Ltd": "387841",
  "Cholamandalam Investment and Finance Co Ltd": "175361",
  "Bank of Baroda": "119553",
  "GAIL (India) Ltd": "1207553",
  "Vedanta Ltd": "784129",
  "NMDC Ltd": "3924993",
  "IndusInd Bank Ltd": "1346049",
  "Torrent Pharma Ltd": "837889",
  "Mphasis Ltd": "3404289",
  "Lupin Ltd": "2672641",
  "Siemens Ltd": "193537",
  "ABB India Ltd": "5633",
  "SRF Ltd": "4107777",
  "Aurobindo Pharma Ltd": "1999361",
  "Bosch Ltd": "558337",
  "Page Industries Ltd": "3689729",
  "Tata Elxsi Ltd": "32504449",
  "Info Edge India Ltd": "2561",
  "Indraprastha Gas Ltd": "2883073",
  "Jindal Steel & Power Ltd": "636673",
  "Balkrishna Industries Ltd": "2873089",
  "Samvardhana Motherson International Ltd": "3834113",
  "ACC Ltd": "160001",
  "Gland Pharma Ltd": "20592641",
  "United Spirits Ltd": "1256193",
  "Marico Ltd": "1041153",
  "Biocon Ltd": "95617",
  "Bandhan Bank Ltd": "4592385",
  "IDFC First Bank Ltd": "1314817",
  "Punjab National Bank": "2713345",
  "Canara Bank": "2752769",
  "TVS Motor Company Ltd": "2883073",
  "Ashok Leyland Ltd": "54273",
  "Bharat Electronics Ltd": "324993",
  "Tata Chemicals Ltd": "2951169",
  "Jubilant FoodWorks Ltd": "2504449",
};

// ============================================================================
// QUERY OPTIONS WITH RETRY & BACKOFF
// ============================================================================

const defaultQueryOptions = {
  retry: 3,
  retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
  staleTime: 30000, // 30 seconds
  refetchOnWindowFocus: false,
};

// ============================================================================
// HELPER FUNCTIONS - Transform API data to Asset format
// ============================================================================

function getSectorFromStockName(name: string): string {
  const techKeywords = ["Infosys", "TCS", "Wipro", "Tech Mahindra", "HCL", "Mphasis", "Tata Elxsi", "Info Edge"];
  const financeKeywords = ["Bank", "HDFC", "ICICI", "Kotak", "Bajaj Finance", "Bajaj Finserv", "Insurance", "SBI Cards", "Cholamandalam"];
  const energyKeywords = ["Reliance", "ONGC", "NTPC", "Power Grid", "Tata Power", "Adani Green", "Adani Transmission", "Coal India", "GAIL", "Indian Oil", "Bharat Petroleum"];
  const autoKeywords = ["Maruti", "Tata Motors", "Mahindra", "Hero", "Eicher", "TVS", "Ashok Leyland"];
  const pharmaKeywords = ["Sun Pharma", "Cipla", "Dr. Reddy", "Divi", "Lupin", "Aurobindo", "Torrent Pharma", "Biocon", "Gland Pharma"];
  const fmcgKeywords = ["Hindustan Unilever", "ITC", "Nestle", "Britannia", "Dabur", "Marico", "Godrej Consumer", "Colgate", "United Spirits"];
  const metalKeywords = ["Tata Steel", "JSW Steel", "Hindalco", "Vedanta", "NMDC", "Jindal Steel"];
  const infraKeywords = ["Larsen", "DLF", "Adani Ports", "Adani Enterprises", "UltraTech", "Shree Cement", "Ambuja", "ACC", "Grasim"];

  if (techKeywords.some((k) => name.includes(k))) return "tech";
  if (financeKeywords.some((k) => name.includes(k))) return "finance";
  if (energyKeywords.some((k) => name.includes(k))) return "energy";
  if (autoKeywords.some((k) => name.includes(k))) return "automotive";
  if (pharmaKeywords.some((k) => name.includes(k))) return "health";
  if (fmcgKeywords.some((k) => name.includes(k))) return "consumer";
  if (metalKeywords.some((k) => name.includes(k))) return "materials";
  if (infraKeywords.some((k) => name.includes(k))) return "infrastructure";
  return "diversified";
}

function transformBondToAsset(bond: BondSummary): Asset {
  // Generate some realistic dummy fields not provided by API
  const hash = bond.isin.charCodeAt(0) + bond.isin.charCodeAt(bond.isin.length - 1);
  
  return {
    id: `bond-${bond.isin}`,
    name: bond.bond_name,
    ticker: bond.isin,
    assetType: "bonds",
    priceOfPar: bond.last_price,
    yieldToMaturity: bond.coupon_rate ? `${(bond.coupon_rate + 0.5).toFixed(2)}%` : "N/A",
    coupon: bond.coupon_rate ? `${bond.coupon_rate.toFixed(2)}%` : "N/A",
    maturityDate: bond.maturity_date,
    duration: parseFloat((4 + (hash % 8)).toFixed(1)),
    changeBps: (hash % 20) - 10,
    region: "asia",
    sector: "bonds",
  };
}

function transformForexToAsset(forex: ForexPairSummary): Asset {
  const isINRPair = forex.pair.includes("INR");
  
  return {
    id: `forex-${forex.pair}`,
    name: forex.pair.replace(/([A-Z]{3})([A-Z]{3})/, "$1/$2"),
    ticker: forex.pair,
    assetType: "forex",
    currentPrice: forex.current_price,
    previousClose: forex.previous_close,
    change: forex.price_change_1d,
    changePercent: forex.price_change_pct_1d,
    high: forex.high_1d,
    low: forex.low_1d,
    region: isINRPair ? "inr" : "major",
    sector: "forex",
  };
}

// ============================================================================
// QUERIES
// ============================================================================

// Return dummy market indices (static data)
export const useMarketIndices = () => {
  return useQuery({
    queryKey: ["market-indices"],
    queryFn: async (): Promise<MarketIndex[]> => {
      // Return static dummy data
      return DUMMY_MARKET_INDICES;
    },
    staleTime: Infinity, // Static data never goes stale
  });
};

// Fetch forex pairs as assets for the table
export const useForexPairs = () => {
  return useQuery({
    queryKey: ["assets", "forex"],
    queryFn: async (): Promise<Asset[]> => {
      const res = await fetch(`${API_BASE}/forex/v1/pairs`);
      if (!res.ok) {
        throw new Error(`Failed to fetch forex pairs: ${res.status}`);
      }
      const data: ForexPairsResponse = await res.json();
      return data.pairs.map(transformForexToAsset);
    },
    ...defaultQueryOptions,
  });
};

// Fetch bonds universe
export const useBondsUniverse = () => {
  return useQuery({
    queryKey: ["assets", "bonds-universe"],
    queryFn: async (): Promise<Asset[]> => {
      const res = await fetch(`${API_BASE}/bonds/universe`);
      if (!res.ok) {
        throw new Error(`Failed to fetch bonds: ${res.status}`);
      }
      const data: BondSummary[] = await res.json();
      return data.map(transformBondToAsset);
    },
    ...defaultQueryOptions,
  });
};

// Generate stocks from real API data
export const useStocksData = () => {
  return useQuery({
    queryKey: ["assets", "stocks"],
    queryFn: async (): Promise<Asset[]> => {
      const res = await fetch(`${API_BASE}/stocks/`);
      console.log("stocks " , res);
      
      if (!res.ok) {
        throw new Error("Failed to fetch available tickers");
      }
      const tickers: string[] = await res.json();
      
      // Fetch latest data for each ticker (limit to 1 to get just the most recent)
      const stocksWithData = await Promise.all(
        tickers.map(async (ticker): Promise<Asset | null> => {
          try {
            const res = await fetch(`${API_BASE}/stocks/${ticker}?limit=1`);
            if (!res.ok) {
              return null;
            }
            const data = await res.json();
            if (data && data.length > 0) {
              const latest = data[data.length - 1]; // Get most recent data point
              return {
                id: ticker,
                name: ticker,
                ticker: ticker,
                assetType: "stocks",
                region: "asia",
                sector: getSectorFromStockName(ticker),
                price: latest.current_price || latest.close_price || 0,
                change: latest.abs_change || 0,
                changePercent: latest.pct_change || 0,
                volume: formatVolume(latest.volume),
                rsi: latest.rsi,
                vwap: latest.vwap,
                signalStrength: latest.signal_strength,
                action: latest.action,
              };
            }
            return null;
          } catch {
            return null;
          }
        })
      );
      
      // Filter out failed fetches
      return stocksWithData.filter((stock): stock is Asset => stock !== null);
    },
    ...defaultQueryOptions,
    staleTime: 60000, 
  });
};

// Helper to format volume
function formatVolume(volume: number): string {
  if (!volume) return "N/A";
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K`;
  return volume.toString();
}

// Hook to get assets based on selected asset class
export const useAssetsByClass = (assetClass: "bonds" | "stocks" | "forex") => {
  const bondsQuery = useBondsUniverse();
  const stocksQuery = useStocksData();
  const forexQuery = useForexPairs();

  switch (assetClass) {
    case "bonds":
      return bondsQuery;
    case "stocks":
      return stocksQuery;
    case "forex":
      return forexQuery;
    default:
      return stocksQuery;
  }
};
