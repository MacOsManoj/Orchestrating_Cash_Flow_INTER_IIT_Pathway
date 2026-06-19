"use client";
import { ChevronRight, X, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { init, dispose, type Chart } from "klinecharts";
import { useAsset } from "@/context/AssetContext";
import { fetchClusters, type NewsCluster } from "@/api/news";
import { fetchStockData, type StockDataPoint } from "@/api/stocks";
import { executeTrade, type TradeRequest } from "@/api/portfolio";
import { useEffect, useState, useRef } from "react";

// Trade Modal Component
interface TradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  tradeType: "buy" | "sell";
  ticker: string;
  assetName: string;
  currentPrice: number;
  onExecute: (quantity: number) => Promise<void>;
  isLoading: boolean;
}

function TradeModal({
  isOpen,
  onClose,
  tradeType,
  ticker,
  assetName,
  currentPrice,
  onExecute,
  isLoading,
}: TradeModalProps) {
  const [quantity, setQuantity] = useState<string>("1");
  const [error, setError] = useState<string>("");

  const totalValue = parseFloat(quantity || "0") * currentPrice;

  const handleSubmit = async () => {
    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setError("Please enter a valid quantity");
      return;
    }
    setError("");
    await onExecute(qty);
    setQuantity("1");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-card border border-border rounded-xl w-full max-w-md"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className={`text-xl font-semibold ${tradeType === "buy" ? "text-green-500" : "text-red-500"}`}>
            {tradeType === "buy" ? "Buy" : "Sell"} {ticker}
          </h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Asset Info */}
          <div className="bg-background/50 rounded-lg p-3">
            <p className="text-sm text-white/60">Asset</p>
            <p className="font-semibold">{assetName}</p>
          </div>

          {/* Current Price */}
          <div className="bg-background/50 rounded-lg p-3">
            <p className="text-sm text-white/60">Current Price</p>
            <p className="font-semibold text-lg">₹{currentPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</p>
          </div>

          {/* Quantity Input */}
          <div>
            <label className="block text-sm text-white/60 mb-2">Quantity</label>
            <input
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary"
              placeholder="Enter quantity"
            />
            {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
          </div>

          {/* Total Value */}
          <div className="bg-background/50 rounded-lg p-3">
            <p className="text-sm text-white/60">Total Value</p>
            <p className="font-bold text-xl">
              ₹{totalValue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border flex gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-border rounded-lg text-white/70 hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50 ${
              tradeType === "buy"
                ? "bg-green-500 hover:bg-green-600 text-white"
                : "bg-red-500 hover:bg-red-600 text-white"
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              `Confirm ${tradeType === "buy" ? "Buy" : "Sell"}`
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export function Stocks() {
  const { selectedAsset } = useAsset();
  const [news, setNews] = useState<NewsCluster[]>([]);
  const [loadingNews, setLoadingNews] = useState(false);
  const [stockDataPoints, setStockDataPoints] = useState<StockDataPoint[]>([]);
  const [loadingStock, setLoadingStock] = useState(false);

  // Trade modal state
  const [tradeModalOpen, setTradeModalOpen] = useState(false);
  const [tradeType, setTradeType] = useState<"buy" | "sell">("buy");
  const [isTrading, setIsTrading] = useState(false);
  const [tradeMessage, setTradeMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Only use selectedAsset if it's actually a stock (not bonds or forex)
  const stockAsset = selectedAsset?.assetType === "stocks" ? selectedAsset : null;

  // Use fetched data if available
  const chartData =
    stockDataPoints.length > 0 && stockDataPoints instanceof Array
      ? stockDataPoints
      : [];
  const latestData = chartData[chartData.length - 1];

  const ticker = latestData?.ticker || stockAsset?.ticker || "ADANIPORTS";
  console.log("Selected asset in Stocks view:", selectedAsset);
  console.log("Stock asset (filtered):", stockAsset);
  useEffect(() => {
    async function loadStockData() {
      setLoadingStock(true);
      try {
        const data = await fetchStockData(ticker);
        setStockDataPoints(data);
      } catch (error) {
        console.error("Failed to fetch stock data", error);
      } finally {
        setLoadingStock(false);
      }
    }
    loadStockData();
  }, [ticker]);


console.log("Chart Data:", chartData);
console.log("Latest Data:", latestData);
  // Derive display data
  const stockData = {
    name: latestData?.ticker || ticker,
    ticker: ticker,
    price: latestData?.close_price || stockAsset?.price || 0,
    change: latestData?.abs_change || stockAsset?.change || 0,
    changePercent: latestData?.pct_change || selectedAsset?.changePercent || 0,
    // marketCap: selectedAsset?.marketCap,
    // peRatio: selectedAsset?.peRatio,
    // dividend: selectedAsset?.dividend,
    volume: latestData?.volume || selectedAsset?.volume,
    currentValue:
      latestData?.current_price || (stockAsset as any)?.currentValue,
    investedAmount: (stockAsset as any)?.investedAmount,
    high: latestData?.high_price || (stockAsset as any)?.high,
    low: latestData?.low_price || (stockAsset as any)?.low,
    recommendation: latestData?.action || "HOLD",
    reason: latestData?.reason || "",
    sentiment: latestData?.signal_strength || 0,
  };


  console.log("Stock Data:", stockData);
  const isPositiveChange = (stockData.change || 0) >= 0;

  // Handle trade execution
  const handleOpenTradeModal = (type: "buy" | "sell") => {
    setTradeType(type);
    setTradeModalOpen(true);
    setTradeMessage(null);
  };

  const handleExecuteTrade = async (quantity: number) => {
    setIsTrading(true);
    try {
      const tradeRequest: TradeRequest = {
        asset_type: "stocks",
        ticker: stockData.ticker,
        action: tradeType,
        quantity: quantity,
        price: stockData.price,
        asset_name: stockData.name,
      };

      const response = await executeTrade(tradeRequest);
      setTradeMessage({ type: "success", text: response.message });
      setTradeModalOpen(false);
      
      // Show success notification for 3 seconds
      setTimeout(() => setTradeMessage(null), 3000);
    } catch (error: any) {
      setTradeMessage({ type: "error", text: error.message || "Trade failed" });
    } finally {
      setIsTrading(false);
    }
  };

  useEffect(() => {
    async function loadNews() {
      if (stockData.name) {
        setLoadingNews(true);
        try {
          const clusters = await fetchClusters({ limit: 3 });
          console.log("Fetched news clusters:", clusters);
          setNews(clusters);
        } catch (error) {
          console.error("Failed to fetch news", error);
        } finally {
          setLoadingNews(false);
        }
      }
    }
    loadNews();
  }, [stockData.name]);

  if (loadingStock) {
    return (
      <div className="min-h-screen bg-background text-white flex items-center justify-center">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-white">
      {/* Trade Modal */}
      <TradeModal
        isOpen={tradeModalOpen}
        onClose={() => setTradeModalOpen(false)}
        tradeType={tradeType}
        ticker={stockData.ticker}
        assetName={stockData.name}
        currentPrice={stockData.price}
        onExecute={handleExecuteTrade}
        isLoading={isTrading}
      />

      {/* Trade Success/Error Notification */}
      {tradeMessage && (
        <div
          className={`fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg ${
            tradeMessage.type === "success"
              ? "bg-green-500 text-white"
              : "bg-red-500 text-white"
          }`}
        >
          {tradeMessage.text}
        </div>
      )}

      {/* Content Area */}
      <div className="px-8 py-6">
        {/* Price Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-primary mb-2">
              {stockData.name} ({stockData.ticker})
            </h2>
            <div className="flex items-baseline gap-3 mb-1">
              <h1 className="text-4xl font-bold">
                Rs. {stockData.price?.toFixed(2)}
              </h1>
              <span
                className={`text-sm ${
                  isPositiveChange ? "text-green-500" : "text-red-500"
                }`}
              >
                {isPositiveChange ? "▲" : "▼"} {isPositiveChange ? "+" : ""}
                {stockData.changePercent?.toFixed(2)}%
              </span>
              <span
                className={`text-sm ${
                  isPositiveChange ? "text-green-500" : "text-red-500"
                }`}
              >
                {isPositiveChange ? "+" : ""}
                {stockData.change?.toFixed(2)} Today
              </span>
            </div>
            <p className="text-xs text-white/70">
              {new Date().toLocaleString()} · INR · NSE
            </p>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={() => handleOpenTradeModal("buy")}
              className="bg-primary hover:bg-primary/80 text-white px-6 py-2 rounded-lg font-medium transition-colors"
            >
              Buy
            </button>
            <button 
              onClick={() => handleOpenTradeModal("sell")}
              className="bg-red-500 hover:bg-red-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
            >
              Sell
            </button>
            <button className="border border-primary text-primary hover:bg-primary/80/10 px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2">
              Compare
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Main Grid */}
        <div className="space-y-2">
          <div className="grid grid-cols-12 gap-3">
            {/* Current Value Card */}
            <div className="col-span-7 bg-card border border-border rounded-lg px-4 py-3">
              <p className="text-xl text-white/70">Current Value:</p>
              <p className="text-3xl font-bold text-red-500 leading-tight">
                Rs. {stockData.currentValue?.toLocaleString("en-IN") || "N/A"}/-
              </p>
              <div className="flex items-center gap-8 mt-2">
                <span>
                  <span className="text-xl text-white/70">
                    Invested amount:{" "}
                  </span>
                  <span className="text-xl font-semibold text-white">
                    Rs.{" "}
                    {stockData.investedAmount?.toLocaleString("en-IN") || "N/A"}
                    /-
                  </span>
                </span>
                <span>
                  <span className="text-xl text-white/70">High/Low: </span>
                  <span className="text-xl font-semibold text-white">
                    Rs. {stockData.high || "N/A"} / {stockData.low || "N/A"}
                  </span>
                </span>
              </div>
            </div>

            {/* Summary Card */}
            <div className="col-span-5 bg-card border  border-primary rounded-lg p-4">
              <h3 className="text-xl font-semibold mb-2">Summary:</h3>
              <div className="space-y-1 text-sm">
                <p className="font-semibold">
                  Recommendation:{" "}
                  <span
                    className={
                      stockData.recommendation === "BUY"
                        ? "text-green-500"
                        : stockData.recommendation === "SELL"
                        ? "text-red-500"
                        : "text-yellow-500"
                    }
                  >
                    {stockData.recommendation}
                  </span>
                </p>
                <p className="text-white/90">
                  • Reason: {stockData.reason.replace(/""/g, '"')}
                </p>
                <p className="text-white/90">
                  • Signal Strength: {stockData.sentiment}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-4">
            {/* Chart Section */}
            <div className="col-span-6 bg-card border border-border rounded-lg p-3">
              {/* Chart (interactive) */}
              <div
                style={{ width: "100%", height: "500px" }}
                className="border border-border rounded"
              >
                <CandlestickChart data={chartData} />
              </div>
            </div>

            {/* Sentiment Analysis Section */}
            <div className="col-span-4 bg-card border border-border rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-semibold">Sentiment Analysis</h3>
                <ChevronRight size={18} className="text-white/70" />
              </div>
              <p className="text-xs text-white/70 mb-1">Sentiment Score</p>
              <div className="mb-3">
                <div className="w-full bg-background rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full"
                    style={{
                      width: `${Math.min(
                        Math.max((stockData.sentiment + 100) / 2, 0),
                        100
                      )}%`,
                    }}
                  ></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-background border border-border rounded-lg p-2 flex flex-col items-center justify-center h-20">
                  <p className="text-xs font-medium">RSI</p>
                  <p className="text-lg font-bold">
                    {latestData?.rsi?.toFixed(2) || "N/A"}
                  </p>
                </div>
                <div className="bg-background border border-border rounded-lg p-2 flex flex-col items-center justify-center h-20">
                  <p className="text-xs font-medium text-white/70">MACD</p>
                  <p className="text-lg font-bold">
                    {latestData?.macd?.toFixed(2) || "N/A"}
                  </p>
                </div>
              </div>
            </div>

            {/* Fundamentals Section */}
            <div className="col-span-2 bg-card border border-border rounded-lg p-3">
              <div className="border-b border-border pb-2 mb-2">
                <span className="text-xl text-primary border-b-2 border-primary pb-2 font-medium">
                  Fundamentals
                </span>
              </div>
              <div className="text-xs space-y-2 overflow-y-auto max-h-[450px]">
                <p className="font-medium">{stockData.name}</p>
                <p className="text-white/80">• Sector: Infrastructure</p>
                {/* <p className="text-white/80">
                  • Market cap: {stockData.marketCap || "N/A"}
                </p>
                <p className="text-white/80">
                  • P/E ratio: {stockData.peRatio || "N/A"}
                </p> */}
                <p className="text-white/80">
                  • VWAP: {latestData?.vwap?.toFixed(2)}
                </p>
                <p className="text-white/80">
                  • Bollinger Bands: {latestData?.bol_bands?.map(v => v.toFixed(2)).join(", ") || "N/A"}
                </p>
                <p className="text-white/80">
                  • CMO: {latestData?.cmo?.toFixed(2) || "N/A"}
                </p>
                <p className="text-white/80">
                  • CRSI: {latestData?.crsi?.toFixed(2) || "N/A"}
                </p>
                <p className="text-white/80">
                  • Keltner: {latestData?.keltner?.map(v => v.toFixed(2)).join(", ") || "N/A"}
                </p>
                <p className="text-white/80">
                  • Klinger: {latestData?.klinger?.map(v => v.toFixed(2)).join(", ") || "N/A"}
                </p>
                <p className="text-white/80">
                  • SMA: {latestData?.sma?.map(v => v.toFixed(2)).join(", ") || "N/A"}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3">News and analytics</h3>
            <div className="grid grid-cols-3 gap-3">
              {loadingNews ? (
                <p className="text-white/70 col-span-3">Loading news...</p>
              ) : news.length > 0 ? (
                news.map((item) => (
                  <NewsCard
                    key={item._id}
                    icon="📰"
                    iconBg="bg-primary/80/20"
                    title={item.title}
                    time={new Date(item.published_at).toLocaleTimeString()}
                    source={item.sources[0] || "Unknown"}
                    summary={item.liquidity_impact || "No summary available"}
                  />
                ))
              ) : (
                <p className="text-white/70 col-span-3">
                  No news found for this asset.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Interactive OHLC candlestick + volume chart
function CandlestickChart({ data }: { data?: Array<any> }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<Chart | null>(null);

  // Parse provided data
  const rawData =
    data && Array.isArray(data) && data.length > 0
      ? data.map((d, i) => {
          // Handle both StockDataPoint and generic data
          const dateStr = d.date || d.time;
          let timestamp = 0;
          if (dateStr) {
            try {
              const dateObj = new Date(dateStr);
              if (!isNaN(dateObj.getTime())) {
                timestamp = dateObj.getTime();
              } else {
                timestamp = new Date().getTime();
              }
            } catch (e) {
              timestamp = new Date().getTime();
            }
          } else {
            // Fallback for mock
            const now = new Date();
            now.setDate(now.getDate() - (50 - i));
            timestamp = now.getTime();
          }

          return {
            timestamp: timestamp,
            open: d.open_price ?? d.open ?? 100,
            high: d.high_price ?? d.high ?? 100,
            low: d.low_price ?? d.low ?? 100,
            close: d.close_price ?? d.close ?? 100,
            volume: d.volume ?? 0,
          };
        })
      : [];

  // Deduplicate by timestamp and sort
  const chartData = Array.from(
    new Map(rawData.map((item) => [item.timestamp, item])).values()
  ).sort((a, b) => a.timestamp - b.timestamp);

  useEffect(() => {
    if (chartContainerRef.current) {
      // Clean up any existing chart instance before initializing
      dispose(chartContainerRef.current);

      // Initialize chart
      const chart = init(chartContainerRef.current);
      chartInstance.current = chart;

      // Set styles to match dark theme
      chart?.setStyles({
        grid: {
          horizontal: { color: "#334155" },
          vertical: { color: "#334155" },
        },
        candle: {
          type: "candle_solid",
          bar: {
            upColor: "#22c55e",
            downColor: "#ef4444",
            noChangeColor: "#888888",
          },
        },
      });

      // Set symbol and period (required for data loader to work in v10)
      chart?.setSymbol({
        ticker: "Stock",
        pricePrecision: 2,
        volumePrecision: 0,
      });
      chart?.setPeriod({ type: "day", span: 1 });

      // Add Volume indicator in a separate pane
      chart?.createIndicator("VOL");

      // Apply data using data loader
      chart?.setDataLoader({
        getBars: (params: any) => {
          if (params.type === "init") {
            params.callback(chartData);
          }
        },
      });

      return () => {
        if (chartContainerRef.current) {
          dispose(chartContainerRef.current);
        }
      };
    }
  }, []); // Run once on mount

  // Update data when it changes
  useEffect(() => {
    if (chartInstance.current && chartData.length > 0) {
      chartInstance.current.setDataLoader({
        getBars: (params: any) => {
          if (params.type === "init") {
            params.callback(chartData);
          }
        },
      });
    }
  }, [chartData]);

  return <div ref={chartContainerRef} style={{ height: "100%" }} />;
}

// News Card Component
interface NewsCardProps {
  icon: string;
  iconBg: string;
  title: string;
  time: string;
  source: string;
  summary: string;
}

function NewsCard({
  icon,
  iconBg,
  title,
  time,
  source,
  summary,
}: NewsCardProps) {
  return (
    <motion.div
      className="bg-background border border-border rounded-lg p-4 hover:border-primary/50 transition-colors cursor-pointer"
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex gap-3 mb-3">
        <div
          className={clsx(
            "w-12 h-12 rounded flex items-center justify-center text-2xl",
            iconBg
          )}
        >
          {icon}
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-medium mb-1 line-clamp-2">{title}</h4>
          <p className="text-xs text-white/70">
            {time} · {source}
          </p>
        </div>
      </div>
      <p className="text-xs text-white/70">{summary}</p>
    </motion.div>
  );
}
