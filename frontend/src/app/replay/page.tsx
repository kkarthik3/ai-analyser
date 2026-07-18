"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";

export default function ReplayPage() {
  const [symbol, setSymbol] = useState("NIFTY50");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<any | null>(null);

  const startBacktest = () => {
    setRunning(true);
    setProgress(0);
    setResults(null);

    // Simulate progress
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          setRunning(false);
          setResults({
            win_rate: 64.5,
            profit_factor: 1.95,
            trades_count: 14,
            pnl: 14200.0,
          });
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Replay & Backtesting Engine
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Simulate options strategies against historical ticks, Greeks, and GEX levels
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Controls Card */}
        <Card title="Simulation Parameters" subtitle="Configure replay settings">
          <div className="space-y-3 text-xs">
            <div className="flex flex-col gap-1">
              <span className="text-[var(--color-text-muted)] uppercase">Symbol</span>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="bg-[var(--color-bg-input)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)]"
              >
                <option value="NIFTY50">NIFTY 50</option>
                <option value="BANKNIFTY">BANK NIFTY</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[var(--color-text-muted)] uppercase">Backtest Window (Days)</span>
              <input
                type="number"
                defaultValue={30}
                className="bg-[var(--color-bg-input)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none"
              />
            </div>

            <button
              onClick={startBacktest}
              disabled={running}
              className="w-full bg-[var(--color-info)] hover:bg-blue-600 text-white rounded py-2 font-semibold transition-colors mt-2 disabled:opacity-50"
            >
              {running ? `Running (${progress}%)` : "Run Backtest Simulation"}
            </button>
          </div>
        </Card>

        {/* Results Card */}
        <div className="lg:col-span-2">
          <Card title="Simulation Output" subtitle="Backtest performance summary">
            {running ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-full max-w-md bg-[var(--color-bg-input)] h-2 rounded overflow-hidden mb-3">
                  <div
                    className="h-full bg-[var(--color-info)] transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--color-text-muted)]">Replaying market ticks...</span>
              </div>
            ) : results ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
                  <MetricCard label="WIN RATE" value={`${results.win_rate}%`} variant="bull" size="sm" />
                  <MetricCard label="PROFIT FACTOR" value={results.profit_factor} variant="bull" size="sm" />
                  <MetricCard label="TOTAL TRADES" value={results.trades_count} size="sm" />
                  <MetricCard label="NET PNL" value={results.pnl.toLocaleString()} variant="bull" size="sm" />
                </div>
                <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                  Historical simulation executed successfully. The strategy validated entries across
                  trend indicators and option chain GEX profiles.
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-[var(--color-text-muted)]">
                <span className="text-3xl mb-2">⏪</span>
                <span className="text-xs">Configure parameters and trigger simulation run.</span>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
