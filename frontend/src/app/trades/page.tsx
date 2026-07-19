"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { getPositions, getHoldings } from "@/lib/api";

type Tab = "positions" | "holdings";

export default function TradesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("positions");
  const [positions, setPositions] = useState<any[]>([]);
  const [holdings, setHoldings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDemoData, setIsDemoData] = useState(false);

  // Mock fallback data to show when API is disconnected or sandbox profile
  const mockPositions = [
    {
      id: "pos_1",
      symbol: "NSE:NIFTY26JUL24500CE",
      direction: "BUY_CE",
      entry_price: 154.5,
      ltp: 182.2,
      qty: 50,
      target_pct: 30.0,
      max_drawdown_limit: -15.0,
      status: "ACTIVE",
    },
    {
      id: "pos_2",
      symbol: "NSE:BANKNIFTY26JUL60000PE",
      direction: "BUY_PE",
      entry_price: 320.1,
      ltp: 290.4,
      qty: 15,
      target_pct: 25.0,
      max_drawdown_limit: -10.0,
      status: "ACTIVE",
    },
  ];

  const mockHoldings = [
    {
      id: "hold_1",
      symbol: "NSE:RELIANCE-EQ",
      direction: "INVESTMENT",
      entry_price: 1250.0,
      ltp: 1327.2,
      qty: 25,
      target_pct: 20.0,
      max_drawdown_limit: -10.0,
      status: "HOLD",
    },
    {
      id: "hold_2",
      symbol: "NSE:TCS-EQ",
      direction: "INVESTMENT",
      entry_price: 2350.0,
      ltp: 2269.0,
      qty: 10,
      target_pct: 15.0,
      max_drawdown_limit: -8.0,
      status: "HOLD",
    },
  ];

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        if (activeTab === "positions") {
          const resp = await getPositions();
          if (resp.s === "ok" && resp.netPositions) {
            setPositions(resp.netPositions);
            setIsDemoData(false);
          } else {
            setPositions(mockPositions);
            setIsDemoData(true);
          }
        } else {
          const resp = await getHoldings();
          if (resp.s === "ok" && resp.holdings) {
            setHoldings(resp.holdings);
            setIsDemoData(false);
          } else {
            setHoldings(mockHoldings);
            setIsDemoData(true);
          }
        }
      } catch (err) {
        console.error("Failed to fetch portfolio data:", err);
        setPositions(mockPositions);
        setHoldings(mockHoldings);
        setIsDemoData(true);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const getExitEngineSuggestion = (pnlPct: number, targetPct: number, drawdownLimit: number) => {
    if (pnlPct >= targetPct) {
      return {
        action: "EXIT (Target reached)",
        variant: "bull",
        description: "Target achieved. Take profit.",
      };
    }
    if (pnlPct <= drawdownLimit) {
      return {
        action: "EXIT (Drawdown limit breached)",
        variant: "bear",
        description: "Hard stop-loss triggered. Exit immediately.",
      };
    }
    if (pnlPct >= targetPct * 0.7) {
      return {
        action: "HOLD (Trailing stop active)",
        variant: "info",
        description: "PnL near target. Protect gains with tight stop.",
      };
    }
    return {
      action: "HOLD (P&L target not reached)",
      variant: "default",
      description: "Stop-loss intact. Position is within normal range.",
    };
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Trade Monitor
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Real-time portfolio tracking, trailing stop-losses, and AI exit recommendations
          </p>
        </div>

        {/* Custom Tab Switcher */}
        <div className="flex bg-[var(--color-bg-elevated)] p-1 rounded-lg border border-[var(--color-border)] self-start md:self-center font-semibold">
          <button
            onClick={() => setActiveTab("positions")}
            className={`px-4 py-1.5 text-xs rounded-md transition-all duration-200 ${
              activeTab === "positions"
                ? "bg-[var(--color-bg-card)] text-[var(--color-text-primary)] shadow-sm"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            }`}
          >
            Positions ({positions.length})
          </button>
          <button
            onClick={() => setActiveTab("holdings")}
            className={`px-4 py-1.5 text-xs rounded-md transition-all duration-200 ${
              activeTab === "holdings"
                ? "bg-[var(--color-bg-card)] text-[var(--color-text-primary)] shadow-sm"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            }`}
          >
            Holdings ({holdings.length})
          </button>
        </div>
      </div>

      {/* Demo Warning Notice */}
      {isDemoData && (
        <div className="bg-[var(--color-info-dim)]/10 border border-[var(--color-info-dim)] px-4 py-3 rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-info)] animate-pulse" />
            <span className="text-xs text-[var(--color-info)] font-medium">
              Demo Mode: Exposing simulated portfolio data for feature preview.
            </span>
          </div>
        </div>
      )}

      {/* Grid of Positions / Holdings */}
      {loading && (activeTab === "positions" ? positions.length === 0 : holdings.length === 0) ? (
        <div className="flex justify-center items-center py-20 text-sm text-[var(--color-text-muted)]">
          Fetching portfolio details...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {activeTab === "positions"
            ? positions.map((pos) => {
                const entry = pos.entry_price || pos.avgPrice || 0;
                const ltp = pos.ltp || pos.lastPrice || 0;
                const qty = pos.qty || pos.netQty || 0;
                const pnl = pos.pnl ?? (ltp - entry) * qty;
                const pnlPct = entry > 0 ? ((ltp - entry) / entry) * 100 : 0;
                const suggestion = getExitEngineSuggestion(
                  pnlPct,
                  pos.target_pct ?? 30.0,
                  pos.max_drawdown_limit ?? -15.0
                );

                return (
                  <Card
                    key={pos.id}
                    title={pos.symbol}
                    subtitle={`Type: ${pos.direction || (qty >= 0 ? "BUY" : "SELL")} | Qty: ${qty}`}
                    headerRight={
                      <span className="text-[10px] bg-[var(--color-bull-dim)] text-[var(--color-bull)] px-2 py-1 rounded font-bold uppercase tracking-wider">
                        Active
                      </span>
                    }
                    glow={pnl >= 0 ? "bull" : "bear"}
                  >
                    <div className="grid grid-cols-2 gap-2 mt-2 font-mono">
                      <MetricCard label="ENTRY PRICE" value={entry.toFixed(2)} size="sm" />
                      <MetricCard label="CURRENT PRICE" value={ltp.toFixed(2)} size="sm" />
                      <MetricCard
                        label="NET PNL"
                        value={pnl.toFixed(2)}
                        variant={pnl >= 0 ? "bull" : "bear"}
                        size="sm"
                      />
                      <MetricCard
                        label="PNL (%)"
                        value={`${pnlPct.toFixed(2)}%`}
                        variant={pnlPct >= 0 ? "bull" : "bear"}
                        size="sm"
                      />
                    </div>

                    <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex flex-col gap-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[var(--color-text-muted)]">Exit Engine Action:</span>
                        <span
                          className={`font-bold uppercase tracking-wider ${
                            suggestion.variant === "bull"
                              ? "text-[var(--color-bull)]"
                              : suggestion.variant === "bear"
                              ? "text-[var(--color-bear)]"
                              : suggestion.variant === "info"
                              ? "text-[var(--color-info)]"
                              : "text-[var(--color-text-secondary)]"
                          }`}
                        >
                          {suggestion.action}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--color-text-muted)] italic font-medium">
                        {suggestion.description}
                      </p>
                    </div>
                  </Card>
                );
              })
            : holdings.map((hold) => {
                const entry = hold.entry_price || hold.costPrice || 0;
                const ltp = hold.ltp || hold.lastPrice || 0;
                const qty = hold.qty || hold.holdingQty || 0;
                const pnl = hold.pnl ?? (ltp - entry) * qty;
                const pnlPct = entry > 0 ? ((ltp - entry) / entry) * 100 : 0;
                const suggestion = getExitEngineSuggestion(
                  pnlPct,
                  hold.target_pct ?? 20.0,
                  hold.max_drawdown_limit ?? -10.0
                );

                return (
                  <Card
                    key={hold.id}
                    title={hold.symbol}
                    subtitle={`Long-Term Asset | Qty: ${qty}`}
                    headerRight={
                      <span className="text-[10px] bg-[var(--color-info-dim)] text-[var(--color-info)] px-2 py-1 rounded font-bold uppercase tracking-wider">
                        Holding
                      </span>
                    }
                    glow={pnl >= 0 ? "bull" : "bear"}
                  >
                    <div className="grid grid-cols-2 gap-2 mt-2 font-mono">
                      <MetricCard label="AVERAGE COST" value={entry.toFixed(2)} size="sm" />
                      <MetricCard label="LAST PRICE" value={ltp.toFixed(2)} size="sm" />
                      <MetricCard
                        label="TOTAL PNL"
                        value={pnl.toFixed(2)}
                        variant={pnl >= 0 ? "bull" : "bear"}
                        size="sm"
                      />
                      <MetricCard
                        label="PNL (%)"
                        value={`${pnlPct.toFixed(2)}%`}
                        variant={pnlPct >= 0 ? "bull" : "bear"}
                        size="sm"
                      />
                    </div>

                    <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex flex-col gap-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[var(--color-text-muted)]">Portfolio Advice:</span>
                        <span
                          className={`font-bold uppercase tracking-wider ${
                            suggestion.variant === "bull"
                              ? "text-[var(--color-bull)]"
                              : suggestion.variant === "bear"
                              ? "text-[var(--color-bear)]"
                              : suggestion.variant === "info"
                              ? "text-[var(--color-info)]"
                              : "text-[var(--color-text-secondary)]"
                          }`}
                        >
                          {suggestion.action}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--color-text-muted)] italic font-medium">
                        {suggestion.description}
                      </p>
                    </div>
                  </Card>
                );
              })}
        </div>
      )}
    </div>
  );
}
