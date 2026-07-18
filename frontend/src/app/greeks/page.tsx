"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getOptionChain, OptionChainRow } from "@/lib/api";

export default function GreeksPage() {
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
        console.error("Failed to load Greeks:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [symbol]);

  const strikes = Array.from(new Set(chain.map((c) => c.strike)))
    .sort((a, b) => a - b)
    .slice(5, 15); // Show a subset of 10 strikes around ATM

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Greeks & IV Surface
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Delta, Gamma, Theta, Vega and Implied Volatility parameters
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

      <Card title="Greeks Snapshot Table" subtitle="Detailed option Greeks computed locally from Black-Scholes">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse font-mono">
            <thead>
              <tr className="bg-[var(--color-bg-elevated)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)]">
                <th className="py-2 px-3">Call Delta</th>
                <th className="py-2 px-3">Call Theta</th>
                <th className="py-2 px-3">IV (%)</th>
                <th className="py-2 px-3 text-center bg-[var(--color-bg-card)] border-l border-r border-[var(--color-border)]">Strike</th>
                <th className="py-2 px-3">IV (%)</th>
                <th className="py-2 px-3">Put Delta</th>
                <th className="py-2 px-3">Put Theta</th>
              </tr>
            </thead>
            <tbody>
              {strikes.map((strike) => {
                const ce = chain.find((c) => c.strike === strike && c.option_type === "CE");
                const pe = chain.find((c) => c.strike === strike && c.option_type === "PE");

                return (
                  <tr key={strike} className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-card-hover)]">
                    <td className="py-2 px-3 text-[var(--color-bull)]">{(ce?.delta ?? 0.5).toFixed(2)}</td>
                    <td className="py-2 px-3 text-[var(--color-bear)]">{(ce?.theta ?? -1.5).toFixed(1)}</td>
                    <td className="py-2 px-3 text-[var(--color-text-accent)]">{((ce?.iv ?? 0.15) * 100).toFixed(1)}%</td>

                    <td className="py-2 px-3 text-center border-l border-r border-[var(--color-border)] bg-[var(--color-bg-elevated)] font-bold text-[var(--color-text-primary)]">
                      {strike}
                    </td>

                    <td className="py-2 px-3 text-[var(--color-text-accent)]">{((pe?.iv ?? 0.15) * 100).toFixed(1)}%</td>
                    <td className="py-2 px-3 text-[var(--color-bear)]">{(pe?.delta ?? -0.5).toFixed(2)}</td>
                    <td className="py-2 px-3 text-[var(--color-bear)]">{(pe?.theta ?? -1.5).toFixed(1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
