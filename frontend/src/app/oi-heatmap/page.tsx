"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getOptionChain, OptionChainRow } from "@/lib/api";

export default function OIHeatmapPage() {
  const [symbol, setSymbol] = useState("NIFTY50");
  const [chain, setChain] = useState<OptionChainRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const resp = await getOptionChain(symbol);
        setChain(resp.data || []);
      } catch (err) {
        console.error("Failed to load chain:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [symbol]);

  // Aggregate option concentrations
  const strikes = Array.from(new Set(chain.map((c) => c.strike)))
    .sort((a, b) => b - a) // Show highest strikes on top
    .slice(0, 10); // Show top 10 strikes

  const getBarWidth = (value: number, max: number) => {
    if (max <= 0) return "0%";
    return `${(value / max) * 100}%`;
  };

  const maxOI = Math.max(...chain.map((c) => c.oi || 1));

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Open Interest Heatmap
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Visualizing strike concentration, volume spikes, and buildup momentum
          </p>
        </div>

        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none"
        >
          <option value="NIFTY50">NIFTY 50</option>
          <option value="NIFTYBANK">BANK NIFTY</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Call concentration */}
        <Card title="Call Open Interest (CE)" subtitle="Top strikes concentration">
          <div className="space-y-3 font-mono">
            {strikes.map((strike) => {
              const ce = chain.find((c) => c.strike === strike && c.option_type === "CE");
              const oi = ce?.oi || 0;
              return (
                <div key={strike} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--color-text-primary)]">{strike}</span>
                    <span className="text-[var(--color-text-secondary)]">{oi.toLocaleString()} OI</span>
                  </div>
                  <div className="h-2 w-full bg-[var(--color-bg-input)] rounded overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-bear)] transition-all duration-500"
                      style={{ width: getBarWidth(oi, maxOI) }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Put concentration */}
        <Card title="Put Open Interest (PE)" subtitle="Top strikes concentration">
          <div className="space-y-3 font-mono">
            {strikes.map((strike) => {
              const pe = chain.find((c) => c.strike === strike && c.option_type === "PE");
              const oi = pe?.oi || 0;
              return (
                <div key={strike} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--color-text-primary)]">{strike}</span>
                    <span className="text-[var(--color-text-secondary)]">{oi.toLocaleString()} OI</span>
                  </div>
                  <div className="h-2 w-full bg-[var(--color-bg-input)] rounded overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-bull)] transition-all duration-500"
                      style={{ width: getBarWidth(oi, maxOI) }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
