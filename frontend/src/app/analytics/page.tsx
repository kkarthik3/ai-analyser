"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState({
    win_rate: 68.4,
    profit_factor: 2.1,
    sharpe_ratio: 1.85,
    sortino_ratio: 2.15,
    max_drawdown: 8.5,
    trade_count: 32,
  });

  const [trades, setTrades] = useState<any[]>([]);

  useEffect(() => {
    setTrades([
      {
        id: "1",
        symbol: "NIFTY50",
        direction: "BUY_CE",
        entry_price: 120.0,
        exit_price: 156.0,
        pnl: 1800.0,
        pnl_pct: 30.0,
        reason: "Profit target hit",
        date: "2026-07-16",
      },
      {
        id: "2",
        symbol: "BANKNIFTY",
        direction: "BUY_PE",
        entry_price: 340.0,
        exit_price: 290.0,
        pnl: -2500.0,
        pnl_pct: -14.7,
        reason: "Stop loss triggered",
        date: "2026-07-15",
      },
    ]);
  }, []);

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
              {trades.map((t) => (
                <tr key={t.id} className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-card-hover)]">
                  <td className="py-2 px-3 text-[var(--color-text-muted)]">{t.date}</td>
                  <td className="py-2 px-3 font-bold text-[var(--color-text-primary)]">{t.symbol}</td>
                  <td className={`py-2 px-3 ${t.direction === "BUY_CE" ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                    {t.direction}
                  </td>
                  <td className="py-2 px-3">{t.entry_price.toFixed(2)}</td>
                  <td className="py-2 px-3">{t.exit_price.toFixed(2)}</td>
                  <td className={`py-2 px-3 ${t.pnl >= 0 ? "text-[var(--color-bull)] font-semibold" : "text-[var(--color-bear)]"}`}>
                    {t.pnl >= 0 ? "+" : ""}{t.pnl.toFixed(1)} ({t.pnl_pct.toFixed(1)}%)
                  </td>
                  <td className="py-2 px-3 text-[var(--color-text-secondary)]">{t.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
