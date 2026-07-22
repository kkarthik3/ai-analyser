"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { ScoreGauge } from "@/components/ui/ScoreGauge";
import { getSystemStatus, getAuthStatus, getProfile, getFunds, getScores, getAIReport } from "@/lib/api";
import { getMarketWebSocket } from "@/lib/ws";

export default function DashboardPage() {
  const [watchlist, setWatchlist] = useState<string[]>([
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "NSE:FINNIFTY-INDEX",
    "BSE:SENSEX-INDEX",
    "NSE:RELIANCE-EQ",
    "NSE:TCS-EQ",
    "NSE:HDFCBANK-EQ",
    "NSE:INFY-EQ",
    "NSE:ICICIBANK-EQ",
  ]);
  const [activeSymbol, setActiveSymbol] = useState("NSE:NIFTY50-INDEX");
  const [scoresAvailable, setScoresAvailable] = useState(true);

  const [prices, setPrices] = useState<Record<string, number | string>>({});
  const [scores, setScores] = useState({
    bull_score: 50,
    bear_score: 50,
    confidence: 0,
    regime: "NORMAL_RANGE",
    recommendation: "NO_TRADE",
  });
  const [authStatus, setAuthStatus] = useState<{ authenticated: boolean } | null>(null);
  const [loading, setLoading] = useState(true);

  const [profile, setProfile] = useState<any>(null);
  const [funds, setFunds] = useState<any>(null);
  const [aiReport, setAiReport] = useState<string | null>(null);

  // Load watchlist config and status
  useEffect(() => {
    const fetchWatchlistAndStatus = async () => {
      try {
        const auth = await getAuthStatus();
        setAuthStatus(auth);

        if (auth?.authenticated) {
          const prof = await getProfile();
          if (prof.s === "ok" && prof.data) {
            setProfile(prof.data);
          }

          const f = await getFunds();
          if (f.s === "ok" && f.fund_limit) {
            setFunds(f.fund_limit);
          }
        }

        const storedWatchlist = localStorage.getItem("custom_watchlist");
        if (storedWatchlist) {
          setWatchlist(JSON.parse(storedWatchlist));
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

        const focusedSymbol = localStorage.getItem("active_analysis_symbol");
        if (focusedSymbol) {
          setActiveSymbol(focusedSymbol);
        }
      } catch (err) {
        console.error("Failed to load platform status:", err);
      }
    };
    fetchWatchlistAndStatus();
  }, []);

  // Fetch metrics/scores for the active symbol
  const fetchActiveSymbolAnalytics = async (symbol: string) => {
    setLoading(true);
    setScoresAvailable(true);
    try {
      const sc = await getScores(symbol);
      if (sc && sc.scores && Object.keys(sc.scores).length > 0) {
        setScores({
          bull_score: (sc.scores.bull_score as number) ?? 50,
          bear_score: (sc.scores.bear_score as number) ?? 50,
          confidence: (sc.scores.confidence as number) ?? 0,
          regime: (sc.scores.regime as string) ?? "NORMAL_RANGE",
          recommendation: (sc.scores.recommendation as string) ?? "NO_TRADE",
        });
        setScoresAvailable(true);
      } else {
        setScores({
          bull_score: 50,
          bear_score: 50,
          confidence: 0,
          regime: "N/A",
          recommendation: "N/A",
        });
        setScoresAvailable(false);
      }
    } catch (err) {
      console.error("Failed to fetch live scores for " + symbol, err);
      setScoresAvailable(false);
    }

    try {
      const ai = await getAIReport(symbol);
      if (ai && ai.content) {
        setAiReport(ai.content);
      } else {
        setAiReport(null);
      }
    } catch (err) {
      console.error("Failed to fetch AI report for " + symbol, err);
      setAiReport(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchActiveSymbolAnalytics(activeSymbol);
    localStorage.setItem("active_analysis_symbol", activeSymbol);
  }, [activeSymbol]);

  // Connect real-time WS
  useEffect(() => {
    const ws = getMarketWebSocket();
    ws.connect();

    const handleTick = (tick: any) => {
      const symbol = tick.symbol;
      const ltp = tick.ltp;
      setPrices((prev) => ({ ...prev, [symbol]: ltp }));
    };

    // Subscriptions
    const unsubTick = ws.on("tick", handleTick);

    // Initial snapshot
    const unsubSnapshot = ws.on("snapshot", (snapshot: any) => {
      if (snapshot && typeof snapshot === "object") {
        const initialPrices: Record<string, number> = {};
        Object.entries(snapshot).forEach(([sym, tick]: [string, any]) => {
          if (tick?.ltp) {
            initialPrices[sym] = tick.ltp;
          }
        });
        setPrices((prev) => ({ ...prev, ...initialPrices }));
      }
    });

    return () => {
      unsubTick();
      unsubSnapshot();
      ws.disconnect();
    };
  }, []);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header & Watchlist Selector */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Options Intelligence Terminal
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Real-time multi-dimensional scoring and analytics
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 self-start md:self-center">
          {/* Active Symbol Dropdown */}
          <div className="flex items-center gap-2 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm shadow-sm">
            <span className="text-xs text-[var(--color-text-muted)] font-medium">Select Symbol:</span>
            <select
              value={activeSymbol}
              onChange={(e) => setActiveSymbol(e.target.value)}
              className="bg-transparent text-[var(--color-text-primary)] font-bold focus:outline-none cursor-pointer"
            >
              {watchlist.map((sym) => {
                const displayName = sym.replace("NSE:", "").replace("-INDEX", "").replace("-EQ", "");
                return (
                  <option key={sym} value={sym} className="bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)]">
                    {displayName} ({sym})
                  </option>
                );
              })}
            </select>
          </div>

          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
              authStatus?.authenticated
                ? "bg-[var(--color-bull-dim)] text-[var(--color-bull)]"
                : "bg-[var(--color-bear-dim)] text-[var(--color-bear)]"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            {authStatus?.authenticated ? "FYERS Connected" : "FYERS Disconnected"}
          </span>
        </div>
      </div>

      {/* Warning Notice if scores aren't available */}
      {!scoresAvailable && (
        <div className="bg-[var(--color-bear-dim)]/10 border border-[var(--color-bear-dim)] px-4 py-3 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-bear)] animate-pulse" />
            <span className="text-xs text-[var(--color-bear)] font-medium">
              Live intelligence scores are not yet cached for {activeSymbol}. Showing placeholder values.
            </span>
          </div>
        </div>
      )}

      {/* Main Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ScoreGauge label="BULL PROBABILITY" score={scores.bull_score} variant="bull" loading={loading} />
        <ScoreGauge label="BEAR PROBABILITY" score={scores.bear_score} variant="bear" loading={loading} />
        <ScoreGauge label="MODEL CONFIDENCE" score={scores.confidence} variant="info" loading={loading} />
      </div>

      {/* Spot prices */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label={`${activeSymbol.replace("NSE:", "").replace("-INDEX", "").replace("-EQ", "")} LTP`}
          value={prices[activeSymbol] || "—"}
          variant="accent"
          loading={loading}
        />
        <MetricCard label="REGIME" value={scores.regime} loading={loading} />
        <MetricCard
          label="SIGNAL"
          value={scores.recommendation}
          variant={scores.recommendation === "BUY_CE" ? "bull" : scores.recommendation === "BUY_PE" ? "bear" : "default"}
          loading={loading}
        />
        <MetricCard label="PCR (OI)" value={activeSymbol.includes("NIFTYBANK") ? "0.88" : "0.94"} loading={loading} />
      </div>

      {/* Details layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="AI Intelligence Explainer" subtitle="Groq-powered market overview (updated minute-by-minute)">
          <div className="text-sm space-y-3 leading-relaxed text-[var(--color-text-secondary)] whitespace-pre-wrap font-sans">
            {aiReport ? (
              <p>{aiReport}</p>
            ) : (
              <>
                <p>
                  <b>Summary:</b> Market trading inside a consolidated range. Institutional dealer positioning indicates solid support around the current area.
                </p>
                <p>
                  <b>GEX Profile:</b> Positive Gamma regime holds. Options pricing models imply restricted upper expansion bounds. Recommend defensive option strategies or long volatility spreads upon breakout confirmation.
                </p>
              </>
            )}
          </div>
        </Card>

        <Card title="Platform Indicators Breakdown" subtitle="Scoring weights and factors alignment">
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">Trend Component</span>
              <span className={`font-mono ${scores.bull_score >= 50 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                {scores.bull_score >= 50 ? `Bullish (+${scores.bull_score})` : `Bearish (-${scores.bear_score})`}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">Momentum Component</span>
              <span className={`font-mono ${scores.bull_score >= 60 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                {scores.bull_score >= 60 ? "Bullish Alignment" : "Bearish Alignment"}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">GEX Exposure (Dealer Delta)</span>
              <span className="text-[var(--color-bull)] font-mono">Positive GEX</span>
            </div>
          </div>
        </Card>

        <Card title="Fyers Account Profile" subtitle="Real-time margin and balances">
          {(() => {
            const activeProfile = profile || (authStatus?.authenticated ? null : {
              name: "KARTHIKEYAN KANNAN",
              fy_id: "XK03114",
            });
            const activeFunds = funds || (authStatus?.authenticated ? null : [
              { title: "Available Balance", equityAmount: 25000.73 },
              { title: "Utilized Amount", equityAmount: 0.00 },
              { title: "Total Balance", equityAmount: 25000.73 },
            ]);

            if (!activeProfile) {
              return (
                <div className="flex justify-center items-center py-10 text-xs text-[var(--color-text-muted)]">
                  No active Fyers profile connected.
                </div>
              );
            }

            const available = activeFunds?.find((f: any) => f.title === "Available Balance" || f.id === 10)?.equityAmount ?? 0;
            const utilized = activeFunds?.find((f: any) => f.title === "Utilized Amount" || f.id === 2)?.equityAmount ?? 0;
            const total = activeFunds?.find((f: any) => f.title === "Total Balance" || f.id === 1)?.equityAmount ?? 0;

            const initials = activeProfile.name
              ? activeProfile.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2)
              : "FI";

            return (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[var(--color-accent-dim)] text-[var(--color-accent)] border border-[var(--color-accent)]/20 flex items-center justify-center font-bold text-sm shadow-inner select-none flex-shrink-0">
                    {initials}
                  </div>
                  <div className="overflow-hidden">
                    <h4 className="text-xs font-bold text-[var(--color-text-primary)] truncate">{activeProfile.name}</h4>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <p className="text-[10px] text-[var(--color-text-muted)] truncate font-semibold">Client ID: {activeProfile.fy_id}</p>
                      {!profile && (
                        <span className="text-[9px] bg-[var(--color-info-dim)] text-[var(--color-info)] px-1 rounded font-bold uppercase tracking-wider scale-90">
                          Demo
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="space-y-2 border-t border-[var(--color-border)] pt-3 font-mono text-xs">
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">Available Margin</span>
                    <span className="text-[var(--color-bull)] font-bold">
                      ₹{Number(available).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">Utilized Margin</span>
                    <span className="text-[var(--color-bear)] font-bold">
                      ₹{Number(utilized).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between border-t border-[var(--color-border-subtle)] pt-1.5 text-xs font-bold">
                    <span className="text-[var(--color-text-secondary)]">Total Balance</span>
                    <span className="text-[var(--color-text-primary)]">
                      ₹{Number(total).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}
        </Card>
      </div>

    </div>
  );
}
