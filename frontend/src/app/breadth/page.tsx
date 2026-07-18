"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { getLatestTicks } from "@/lib/api";

export default function BreadthPage() {
  const [ticks, setTicks] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const resp = await getLatestTicks();
        setTicks(resp.data || {});
      } catch (err) {
        console.error("Failed to load tick states:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const totalWatch = Object.keys(ticks).length;
  // Advance/Decline ratio estimation from tick returns
  const advances = Object.values(ticks).filter((t: any) => (t.change_pct || 0) > 0).length;
  const declines = Object.values(ticks).filter((t: any) => (t.change_pct || 0) < 0).length;
  const adRatio = declines > 0 ? (advances / declines).toFixed(2) : advances.toFixed(2);

  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Market Breadth Dashboard
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Tracking Advance-Decline metrics and relative watchlist momentum
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard label="ADVANCES" value={advances} variant="bull" loading={loading} />
        <MetricCard label="DECLINES" value={declines} variant="bear" loading={loading} />
        <MetricCard label="A/D RATIO" value={adRatio} variant="info" loading={loading} />
      </div>

      <Card title="Watchlist Securities Momentum" subtitle="Snapshot of current ticker returns">
        <div className="space-y-3 font-mono">
          {Object.entries(ticks).map(([symbol, tick]: [string, any]) => {
            const chg = tick.change_pct || 0.0;
            return (
              <div key={symbol} className="flex justify-between items-center text-xs py-1 border-b border-[var(--color-border-subtle)]">
                <span className="text-[var(--color-text-primary)]">{symbol}</span>
                <div className="flex gap-4">
                  <span className="text-[var(--color-text-secondary)]">LTP: {tick.ltp}</span>
                  <span className={chg >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}>
                    {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
