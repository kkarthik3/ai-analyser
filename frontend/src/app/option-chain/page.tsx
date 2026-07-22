"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getOptionChain, getOptionChainExpiries, OptionChainRow } from "@/lib/api";

export default function OptionChainPage() {
  const [symbol, setSymbol] = useState("NSE:NIFTY50-INDEX");
  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<string>("");
  const [chain, setChain] = useState<OptionChainRow[]>([]);
  const [loading, setLoading] = useState(true);

  const underlying = symbol === "NSE:NIFTY50-INDEX" ? "NIFTY50" : "NIFTYBANK";

  // Fetch expiries whenever index changes
  useEffect(() => {
    const fetchExpiries = async () => {
      try {
        const exps = await getOptionChainExpiries(underlying);
        if (Array.isArray(exps) && exps.length > 0) {
          setExpiries(exps);
          setSelectedExpiry(exps[0]); // default to nearest expiry
        } else {
          setExpiries([]);
          setSelectedExpiry("");
        }
      } catch (err) {
        console.error("Failed to load expiries:", err);
      }
    };
    fetchExpiries();
  }, [symbol]);

  const fetchChainData = async () => {
    if (!selectedExpiry) return;
    setLoading(true);
    try {
      const resp = await getOptionChain(underlying, selectedExpiry);
      setChain(resp.data || []);
    } catch (err) {
      console.error("Failed to fetch option chain:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChainData();
    const timer = setInterval(fetchChainData, 5000);
    return () => clearInterval(timer);
  }, [symbol, selectedExpiry]);

  // Separate calls and puts for strikes
  const strikes = Array.from(new Set(chain.map((c) => c.strike))).sort((a, b) => a - b);

  const getOptionForStrike = (strike: number, type: "CE" | "PE") => {
    return chain.find((c) => c.strike === strike && c.option_type === type);
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Live Option Chain
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Real-time open interest concentration, volume, and Greeks
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Index selector */}
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-border-focus)] font-semibold"
          >
            <option value="NSE:NIFTY50-INDEX">NIFTY 50</option>
            <option value="NSE:NIFTYBANK-INDEX">BANK NIFTY</option>
          </select>

          {/* Expiry selector */}
          {expiries.length > 0 && (
            <select
              value={selectedExpiry}
              onChange={(e) => setSelectedExpiry(e.target.value)}
              className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-border-focus)] font-semibold"
            >
              {expiries.map((exp) => (
                <option key={exp} value={exp}>
                  Expiry: {exp}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <Card title="Chain Grid" subtitle={`Sorted by strike for Expiry: ${selectedExpiry || "None"} (ATM highlighted)`}>
        {loading && chain.length === 0 ? (
          <div className="flex justify-center items-center py-16 text-sm text-[var(--color-text-muted)]">
            Loading option chain data...
          </div>
        ) : chain.length === 0 ? (
          <div className="flex justify-center items-center py-16 text-sm text-[var(--color-text-muted)]">
            No options data available for this expiry date. Ensure options poller is running.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[var(--color-bg-elevated)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] uppercase">
                  <th className="py-2 px-3 text-center" colSpan={4}>Calls (CE)</th>
                  <th className="py-2 px-3 text-center border-l border-r border-[var(--color-border)]">Strike</th>
                  <th className="py-2 px-3 text-center" colSpan={4}>Puts (PE)</th>
                </tr>
                <tr className="bg-[var(--color-bg-card)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] text-[10px]">
                  <th className="py-1.5 px-3">OI</th>
                  <th className="py-1.5 px-3">Chg OI</th>
                  <th className="py-1.5 px-3">Volume</th>
                  <th className="py-1.5 px-3 text-right">LTP</th>
                  <th className="py-1.5 px-3 text-center border-l border-r border-[var(--color-border)] bg-[var(--color-bg-elevated)]">Price</th>
                  <th className="py-1.5 px-3">LTP</th>
                  <th className="py-1.5 px-3">Volume</th>
                  <th className="py-1.5 px-3">Chg OI</th>
                  <th className="py-1.5 px-3 text-right">OI</th>
                </tr>
              </thead>
              <tbody>
                {strikes.map((strike) => {
                  const ce = getOptionForStrike(strike, "CE");
                  const pe = getOptionForStrike(strike, "PE");

                  return (
                    <tr
                      key={strike}
                      className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-card-hover)] font-mono"
                    >
                      {/* Calls fields */}
                      <td className="py-2 px-3 text-[var(--color-text-primary)]">{ce?.oi?.toLocaleString() ?? "0"}</td>
                      <td className={`py-2 px-3 ${(ce?.change_oi ?? 0) >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                        {(ce?.change_oi ?? 0) > 0 ? "+" : ""}{ce?.change_oi?.toLocaleString() ?? "0"}
                      </td>
                      <td className="py-2 px-3 text-[var(--color-text-secondary)]">{ce?.volume?.toLocaleString() ?? "0"}</td>
                      <td className="py-2 px-3 text-right text-[var(--color-bull)] font-semibold">{ce?.ltp ?? "—"}</td>

                      {/* Strike */}
                      <td className="py-2 px-3 text-center border-l border-r border-[var(--color-border)] bg-[var(--color-bg-elevated)] font-bold text-[var(--color-text-primary)]">
                        {strike}
                      </td>

                      {/* Puts fields */}
                      <td className="py-2 px-3 text-bear font-semibold">{pe?.ltp ?? "—"}</td>
                      <td className="py-2 px-3 text-[var(--color-text-secondary)]">{pe?.volume?.toLocaleString() ?? "0"}</td>
                      <td className={`py-2 px-3 ${(pe?.change_oi ?? 0) >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                        {(pe?.change_oi ?? 0) > 0 ? "+" : ""}{pe?.change_oi?.toLocaleString() ?? "0"}
                      </td>
                      <td className="py-2 px-3 text-right text-[var(--color-text-primary)]">{pe?.oi?.toLocaleString() ?? "0"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
