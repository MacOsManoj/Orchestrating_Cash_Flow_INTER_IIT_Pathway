
export interface StockDataPoint {
  ticker: string;
  date: string;
  close_price: number;
  open_price: number;
  volume: number;
  high_price: number;
  low_price: number;
  abs_change: number;
  pct_change: number;
  action: string;
  stop_loss: number;
  take_profit: number;
  signal_strength: number;
  limit_order: number;
  current_price: number;
  rsi: number;
  macd: number;
  macd_signal: number;
  macd_hist: number;
  vwap: number;
  bol_bands: [number, number];
  sma: [number, number];
  crsi: number;
  klinger: [number, number, number];
  keltner: [number, number, number];
  cmo: number;
  reason: string;
  time: number;
  diff: number;
}

const rawData = `
"ticker","date","close_price","open_price","volume","high_price","low_price","abs_change","pct_change","action","stop_loss","take_profit","signal_strength","limit_order","current_price","rsi","macd","macd_signal","macd_hist","vwap","bol_bands","sma","crsi","klinger","keltner","cmo","reason","time","diff"
"ADANIPORTS","2025-08-25T09:15:00+05:30","1415.05","1413.05","35830.0","1416.1","1410.05","0.0","0.0","HOLD","0.0","0.0","0.0","0.0","1415.05","50.0","0.0","0.0","0.0","1413.7333333333331","[0.0,0.0]","[0.0,0.0]","50.0","[0.0,0.0,0.0]","[1415.05,1415.05,1415.05]","0.0","""vwap says BUY, keltner_low says BUY, kelt_up says SELL, ""","1765008546340","1"
"ADANIPORTS","2025-08-25T09:20:00+05:30","1414.5","1415.05","18097.0","1415.05","1412.4","0.0","0.0","HOLD","0.0","0.0","0.0","0.0","1414.5","0.0","0.04387464387491491","0.008774928774982982","0.03509971509993193","1413.817229155463","[0.0,0.0]","[0.0,0.0]","50.0","[0.0,0.0,0.0]","[1414.997619047619,1423.697619047619,1406.2976190476193]","-100.0","""macd says BUY, vwap says BUY, cmo says BUY, ""","1765008547594","1"
"ADANIPORTS","2025-08-25T09:25:00+05:30","1415.6","1414.5","8021.0","1416.9","1413.35","0.0","0.0","HOLD","0.0","0.0","0.0","0.0","1415.6","66.66666666666666","0.12162401279238112","0.03134474557846261","0.09027926721391848","1414.0070596844666","[0.0,0.0]","[0.0,0.0]","61.11111111111111","[-215.9142857142906,-30.84489795918437,-185.06938775510625]","[1415.0549886621316,1423.2216553287983,1406.8883219954648]","33.333333333333336","""macd says BUY, vwap says BUY, rsi says SELL, klinger says SELL, cmo says SELL, ""","1765008549094","1"
"ADANIPORTS","2025-08-25T09:30:00+05:30","1416.15","1415.9","11691.0","1416.7","1413.1","0.0","0.0","HOLD","0.0","0.0","0.0","0.0","1416.15","75.00000000000259","0.2250273757586001","0.07008127161449011","0.15494610414410998","1414.214974175822","[0.0,0.0]","[0.0,0.0]","62.777777777778645","[-333.13653061224977,-74.02941690962228,-259.1071137026275]","[1415.1592754562143,1423.0842754562143,1407.2342754562142]","50.000000000005166","""macd says BUY, vwap says BUY, klinger says SELL, cmo says SELL, ""","1765008549094","1"
"ADANIPORTS","2025-08-25T09:35:00+05:30","1414.4","1416.15","10672.0","1416.15","1413.65","0.0","0.0","HOLD","0.0","0.0","0.0","0.0","1414.4","41.772151898736","0.24726815033091043","0.08016383031583756","0.16710432001507286","1414.2805875469","[0.0,0.0]","[0.0,0.0]","19.24210098547243","[-918.2403542274096,-194.63097938359192,-723.6093748438177]","[1415.0869635080037,1422.4269635080036,1407.746963508003]","-16.455696202528003","""macd says BUY, rsi says BUY, crsi says BUY, vwap says BUY, klinger says SELL, ""","1765008550594","1"
"ADANIPORTS","2025-08-25T09:45:00+05:30","1413.2","1415.45","4177.0","1415.45","1413.2","0.0","0.0","HOLD","0.0","0.0","0.0","0.0","1413.2","37.241379310345465","0.6030615236579706","0.2995382807077227","0.3035232429502479","1414.2959884609966","[0.0,0.0]","[0.0,0.0]","19.305036049222107","[-1508.3683839521527,-498.05642453598455,-1010.3119594161682]","[1414.9385347537172,1421.4956776108602,1408.3813918965743]","-25.51724137930909","""macd says BUY, rsi says BUY, crsi says BUY, vwap says SELL, klinger says SELL, ""","1765008552094","1"
"ADANIPORTS","2025-08-25T09:40:00+05:30","1415.45","1414.4","3721.0","1416.0","1413.65","0.0","0.0","HOLD","0.0","0.0","0.0","0.0","1415.45","54.00000000000091","0.2872883261104562","0.11155899270313466","0.17572933340732153","1414.3124051481282","[0.0,0.0]","[0.0,0.0]","58.81071585419421","[-1139.911809464811,-329.6710979666232,-810.2407114981879]","[1415.1215384120032,1422.021538412003,1408.2215384120032]","8.000000000001819","""macd says BUY, vwap says BUY, klinger says SELL, ""","1765008552094","1"
`;

export function parseStockData(csvData: string = rawData): StockDataPoint[] {
  const lines = csvData.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.replace(/"/g, ''));
  
  return lines.slice(1).map(line => {
    // Handle the complex CSV parsing (especially for array fields like "[0.0,0.0]")
    // This is a simple regex based parser for the specific format provided
    const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || [];
    const values = matches.map(val => val.replace(/^"|"$/g, '')); // Remove surrounding quotes
    
    // If simple split fails due to commas in arrays, we need a more robust approach
    // But for the provided sample, let's try to map by index manually if needed
    // Or better, use a proper CSV parser logic
    
    const entry: any = {};
    
    // Manual parsing because of the complex array strings
    // We can split by `","` which seems consistent in the input
    const cleanLine = line.substring(1, line.length - 1); // Remove first and last quote
    const parts = cleanLine.split('","');
    
    if (parts.length !== headers.length) {
        // Fallback or error handling
        console.warn('Mismatch in CSV parts', parts.length, headers.length);
        return null;
    }

    headers.forEach((header, index) => {
      const value = parts[index];
      
      if (['close_price', 'open_price', 'volume', 'high_price', 'low_price', 'abs_change', 'pct_change', 'stop_loss', 'take_profit', 'signal_strength', 'limit_order', 'current_price', 'rsi', 'macd', 'macd_signal', 'macd_hist', 'vwap', 'crsi', 'cmo', 'time', 'diff'].includes(header)) {
        entry[header] = parseFloat(value);
      } else if (['bol_bands', 'sma', 'klinger', 'keltner'].includes(header)) {
        try {
          entry[header] = JSON.parse(value);
        } catch (e) {
          entry[header] = [];
        }
      } else {
        entry[header] = value;
      }
    });

    return entry as StockDataPoint;
  }).filter(item => item !== null) as StockDataPoint[];
}

export const SAMPLE_STOCK_DATA = parseStockData();
