"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { getLatestTicks, getSystemStatus } from "@/lib/api";
import { getMarketWebSocket } from "@/lib/ws";

export default function BreadthPage() {
  const router = useRouter();
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [ticks, setTicks] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);

  // Input form state
  const [newSymbol, setNewSymbol] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  // 1. Initial watchlist loading (localStorage fallback to backend config)
  useEffect(() => {
    const loadWatchlist = async () => {
      try {
        const stored = localStorage.getItem("custom_watchlist");
        if (stored) {
          setWatchlist(JSON.parse(stored));
        } else {
          const status = await getSystemStatus();
          if (status?.config) {
            const indices = (status.config.watchlist_indices as string[]) || [];
            const stocks = (status.config.watchlist_stocks as string[]) || [];
            const combined = [...indices, ...stocks];
            if (combined.length > 0) {
              setWatchlist(combined);
              localStorage.setItem("custom_watchlist", JSON.stringify(combined));
            }
          }
        }
      } catch (err) {
        console.error("Failed to load watchlist status:", err);
      }
    };
    loadWatchlist();
  }, []);

  // 2. Fetch tick details whenever watchlist changes
  const fetchTicks = async () => {
    if (watchlist.length === 0) {
      setTicks({});
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const resp = await getLatestTicks(watchlist.join(","));
      setTicks(resp.data || {});
    } catch (err) {
      console.error("Failed to fetch ticks for watchlist:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTicks();
  }, [watchlist]);

  // 3. Connect real-time WebSocket for live price updates
  useEffect(() => {
    const ws = getMarketWebSocket();
    ws.connect();

    const handleTick = (tick: any) => {
      const symbol = tick.symbol;
      setTicks((prev) => {
        if (!prev[symbol]) {
          return {
            ...prev,
            [symbol]: tick,
          };
        }
        return {
          ...prev,
          [symbol]: {
            ...prev[symbol],
            ltp: tick.ltp,
            change_pct: tick.change_pct ?? prev[symbol].change_pct ?? 0.0,
            volume: tick.volume ?? prev[symbol].volume ?? 0,
            open: tick.open ?? prev[symbol].open ?? 0,
            high: tick.high ?? prev[symbol].high ?? 0,
            low: tick.low ?? prev[symbol].low ?? 0,
            close: tick.close ?? prev[symbol].close ?? 0,
          },
        };
      });
    };

    const unsubTick = ws.on("tick", handleTick);

    const unsubSnapshot = ws.on("snapshot", (snapshot: any) => {
      if (snapshot && typeof snapshot === "object") {
        setTicks((prev) => {
          const updated = { ...prev };
          Object.entries(snapshot).forEach(([sym, tick]: [string, any]) => {
            if (tick) {
              updated[sym] = {
                ...(updated[sym] || {}),
                ...tick,
              };
            }
          });
          return updated;
        });
      }
    });

    return () => {
      unsubTick();
      unsubSnapshot();
      ws.disconnect();
    };
  }, []);

  // 4. Watchlist addition
  const handleAddSymbol = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");

    let cleanSymbol = newSymbol.trim().toUpperCase();
    if (!cleanSymbol) return;

    // Add NSE prefix if not present and no exchange is specified
    if (!cleanSymbol.includes(":")) {
      cleanSymbol = `NSE:${cleanSymbol}`;
    }

    if (watchlist.includes(cleanSymbol)) {
      setErrorMessage("Symbol is already in your watchlist.");
      return;
    }

    const updated = [...watchlist, cleanSymbol];
    setWatchlist(updated);
    localStorage.setItem("custom_watchlist", JSON.stringify(updated));
    setNewSymbol("");
  };

  // 5. Watchlist removal
  const handleRemoveSymbol = (symbolToRemove: string) => {
    const updated = watchlist.filter((sym) => sym !== symbolToRemove);
    setWatchlist(updated);
    localStorage.setItem("custom_watchlist", JSON.stringify(updated));
  };

  // 6. Navigate to analyze on dashboard
  const handleAnalyze = (sym: string) => {
    localStorage.setItem("active_analysis_symbol", sym);
    router.push("/");
  };

  const totalWatch = watchlist.length;
  const advances = watchlist.filter((sym) => (ticks[sym]?.change_pct || 0) > 0).length;
  const declines = watchlist.filter((sym) => (ticks[sym]?.change_pct || 0) < 0).length;
  const adRatio = declines > 0 ? (advances / declines).toFixed(2) : advances.toFixed(2);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Title & Info */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Watchlist Momentum Dashboard
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Real-time ticker metrics, custom watchlist additions, and advances/declines momentum
          </p>
        </div>
      </div>

      {/* Ticker advances/declines row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard label="ADVANCES" value={advances} variant="bull" loading={loading} />
        <MetricCard label="DECLINES" value={declines} variant="bear" loading={loading} />
        <MetricCard label="A/D RATIO" value={adRatio} variant="info" loading={loading} />
      </div>

      {/* Add Symbol Section */}
      <Card title="Add Watchlist Symbol" subtitle="Customize the tickers tracked on your intelligence panel">
        <form onSubmit={handleAddSymbol} className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="e.g. RELIANCE-EQ, NIFTYBANK-INDEX or NSE:SBIN-EQ"
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-border-focus)] font-mono"
            />
            {errorMessage && (
              <p className="text-xs text-[var(--color-bear)] mt-1 font-medium">{errorMessage}</p>
            )}
          </div>
          <button
            type="submit"
            className="bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent)]/90 font-semibold text-xs px-5 py-2.5 rounded-md transition-all duration-200 shadow-sm shrink-0 self-start sm:self-center"
          >
            + Add Ticker
          </button>
        </form>
        <div className="mt-3">
          <span className="text-[10px] text-[var(--color-text-muted)] font-semibold uppercase tracking-wider block mb-1.5">
            Quick Suggestions:
          </span>
          <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
            {["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:FINNIFTY-INDEX", "NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:HDFCBANK-EQ"].map((s) => (
              <button
                key={s}
                onClick={() => {
                  setNewSymbol(s);
                  setErrorMessage("");
                }}
                className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-muted)] px-2 py-1 rounded transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Custom Watchlist Table */}
      <Card title="Watchlist Securities Momentum" subtitle="Snapshot of current ticker returns and detailed spreads">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="bg-[var(--color-bg-elevated)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] uppercase text-[10px]">
                <th className="py-2.5 px-3">Symbol</th>
                <th className="py-2.5 px-3">Price (LTP)</th>
                <th className="py-2.5 px-3">Change (%)</th>
                <th className="py-2.5 px-3">High / Low</th>
                <th className="py-2.5 px-3">Volume</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {watchlist.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-sm text-[var(--color-text-muted)]">
                    No symbols in your custom watchlist. Use the card above to add some!
                  </td>
                </tr>
              ) : (
                watchlist.map((sym) => {
                  const tick = ticks[sym];
                  const ltp = tick?.ltp ?? "—";
                  const chg = tick?.change_pct ?? 0.0;
                  const high = tick?.high ?? "—";
                  const low = tick?.low ?? "—";
                  const volume = tick?.volume ? tick.volume.toLocaleString() : "—";
                  const cleanName = sym.replace("NSE:", "").replace("-INDEX", "").replace("-EQ", "");

                  return (
                    <tr
                      key={sym}
                      className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-card-hover)]"
                    >
                      <td className="py-3 px-3">
                        <span className="font-bold text-[var(--color-text-primary)] block">{cleanName}</span>
                        <span className="text-[10px] text-[var(--color-text-muted)] font-semibold">{sym}</span>
                      </td>
                      <td className="py-3 px-3 font-semibold text-[var(--color-text-primary)]">
                        {typeof ltp === "number" ? `₹${ltp.toFixed(2)}` : ltp}
                      </td>
                      <td className={`py-3 px-3 font-bold ${chg >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                        {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
                      </td>
                      <td className="py-3 px-3 text-[var(--color-text-secondary)]">
                        {high !== "—" ? `₹${high}` : "—"} / {low !== "—" ? `₹${low}` : "—"}
                      </td>
                      <td className="py-3 px-3 text-[var(--color-text-secondary)]">{volume}</td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleAnalyze(sym)}
                            className="bg-[var(--color-accent-dim)]/20 text-[var(--color-accent)] hover:bg-[var(--color-accent-dim)]/30 border border-[var(--color-accent)]/20 font-semibold px-2.5 py-1 rounded text-[11px] transition-colors"
                          >
                            Analyze
                          </button>
                          <button
                            onClick={() => handleRemoveSymbol(sym)}
                            className="bg-[var(--color-bear-dim)]/20 text-[var(--color-bear)] hover:bg-[var(--color-bear-dim)]/30 border border-[var(--color-bear)]/20 font-semibold px-2.5 py-1 rounded text-[11px] transition-colors"
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
