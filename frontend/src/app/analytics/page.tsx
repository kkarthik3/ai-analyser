"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { getTradeJournal, getTradeAnalytics } from "@/lib/api";

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState({
    win_rate: 0,
    profit_factor: 0,
    sharpe_ratio: 0,
    sortino_ratio: 0,
    max_drawdown: 0,
    trade_count: 0,
  });

  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalyticsData = async () => {
      setLoading(true);
      try {
        const [journalResp, analyticsResp] = await Promise.all([
          getTradeJournal(),
          getTradeAnalytics(),
        ]);

        if (Array.isArray(journalResp)) {
          setTrades(journalResp);
        }

        if (analyticsResp && typeof analyticsResp.win_rate === "number") {
          setMetrics(analyticsResp);
        }
      } catch (err) {
        console.error("Failed to load historical analytics data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalyticsData();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20 text-sm text-[var(--color-text-muted)] animate-pulse">
        Loading historical trade analytics...
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Historical Analytics
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Scoring calibration and historical trade journal logs
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard label="WIN RATE" value={`${metrics.win_rate}%`} variant="bull" />
        <MetricCard label="PROFIT FACTOR" value={metrics.profit_factor} variant="bull" />
        <MetricCard label="SHARPE RATIO" value={metrics.sharpe_ratio} variant="info" />
        <MetricCard label="SORTINO RATIO" value={metrics.sortino_ratio} variant="info" />
        <MetricCard label="MAX DRAWDOWN" value={`${metrics.max_drawdown}%`} variant="bear" />
        <MetricCard label="TOTAL TRADES" value={metrics.trade_count} />
      </div>

      {/* Trade Journal Table */}
      <Card title="Trade Journal logs" subtitle="Audit trail of historical strategy execution">
        <div className="overflow-x-auto font-mono text-xs">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-bg-elevated)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] uppercase text-[10px]">
                <th className="py-2 px-3">Date</th>
                <th className="py-2 px-3">Symbol</th>
                <th className="py-2 px-3">Type</th>
                <th className="py-2 px-3">Entry</th>
                <th className="py-2 px-3">Exit</th>
                <th className="py-2 px-3">PnL (%)</th>
                <th className="py-2 px-3">Reason</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-sm text-[var(--color-text-muted)]">
                    No historical trade journal entries found in the database.
                  </td>
                </tr>
              ) : (
                trades.map((t) => {
                  const directionStr = String(t.direction || "").toUpperCase();
                  const isBullishType = directionStr.includes("BUY") || directionStr.includes("CE");
                  return (
                    <tr key={t.id} className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-card-hover)]">
                      <td className="py-2 px-3 text-[var(--color-text-muted)]">{t.date}</td>
                      <td className="py-2 px-3 font-bold text-[var(--color-text-primary)]">{t.symbol}</td>
                      <td className={`py-2 px-3 ${isBullishType ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                        {t.direction}
                      </td>
                      <td className="py-2 px-3">{(t.entry_price || 0).toFixed(2)}</td>
                      <td className="py-2 px-3">{(t.exit_price || 0).toFixed(2)}</td>
                      <td className={`py-2 px-3 ${t.pnl >= 0 ? "text-[var(--color-bull)] font-semibold" : "text-[var(--color-bear)]"}`}>
                        {t.pnl >= 0 ? "+" : ""}{(t.pnl || 0).toFixed(1)} ({(t.pnl_pct || 0).toFixed(1)}%)
                      </td>
                      <td className="py-2 px-3 text-[var(--color-text-secondary)]">{t.reason}</td>
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
