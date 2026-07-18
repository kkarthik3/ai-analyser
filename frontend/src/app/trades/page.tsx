"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";

export default function TradesPage() {
  const [positions, setPositions] = useState<any[]>([]);

  useEffect(() => {
    // Inject a mock active trade to demonstrate Phase 3 exit monitoring
    setPositions([
      {
        id: "1",
        symbol: "NIFTY5024JUL24500CE",
        direction: "BUY_CE",
        entry_price: 154.5,
        ltp: 182.2,
        qty: 50,
        target_pct: 30.0,
        max_drawdown_limit: -15.0,
        entry_time: new Date().toLocaleTimeString(),
      },
    ]);
  }, []);

  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Trade Monitor
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Real-time position monitoring, trailing stops, and exit suggestions
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {positions.map((pos) => {
          const pnl = (pos.ltp - pos.entry_price) * pos.qty;
          const pnlPct = ((pos.ltp - pos.entry_price) / pos.entry_price) * 100;

          return (
            <Card
              key={pos.id}
              title={pos.symbol}
              subtitle={`Direction: ${pos.direction} | Qty: ${pos.qty}`}
              headerRight={
                <span className="text-xs bg-[var(--color-bull-dim)] text-[var(--color-bull)] px-2 py-1 rounded font-bold">
                  ACTIVE
                </span>
              }
            >
              <div className="grid grid-cols-2 gap-3 mt-2 font-mono">
                <MetricCard label="ENTRY PRICE" value={pos.entry_price} size="sm" />
                <MetricCard label="CURRENT PRICE" value={pos.ltp} size="sm" />
                <MetricCard label="NET PNL" value={pnl.toFixed(2)} variant={pnl >= 0 ? "bull" : "bear"} size="sm" />
                <MetricCard label="PNL (%)" value={`${pnlPct.toFixed(2)}%`} variant={pnlPct >= 0 ? "bull" : "bear"} size="sm" />
              </div>

              <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex items-center justify-between text-xs">
                <span className="text-[var(--color-text-muted)]">Exit Engine Action:</span>
                <span className="text-[var(--color-bull)] font-bold uppercase animate-pulse">
                  HOLD (P&L target not reached)
                </span>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
