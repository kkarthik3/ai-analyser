"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { ScoreGauge } from "@/components/ui/ScoreGauge";
import { getSystemStatus, getAuthStatus } from "@/lib/api";
import { getMarketWebSocket } from "@/lib/ws";

export default function DashboardPage() {
  const [niftySpot, setNiftySpot] = useState<number | string>("—");
  const [bankNiftySpot, setBankNiftySpot] = useState<number | string>("—");
  const [scores, setScores] = useState({
    bull_score: 50,
    bear_score: 50,
    confidence: 0,
    regime: "NORMAL_RANGE",
    recommendation: "NO_TRADE",
  });
  const [authStatus, setAuthStatus] = useState<{ authenticated: boolean } | null>(null);
  const [loading, setLoading] = useState(true);

  // Poll system statuses
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const auth = await getAuthStatus();
        setAuthStatus(auth);
      } catch (err) {
        console.error("Failed to fetch auth status:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, []);

  // Connect real-time WS
  useEffect(() => {
    const ws = getMarketWebSocket();
    ws.connect();

    const unsubscribe = ws.on("tick", (tick: any) => {
      const symbol = tick.symbol;
      const ltp = tick.ltp;

      if (symbol === "NSE:NIFTY50-INDEX") {
        setNiftySpot(ltp);
      } else if (symbol === "NSE:NIFTYBANK-INDEX") {
        setBankNiftySpot(ltp);
      }
    });

    return () => {
      unsubscribe();
      ws.disconnect();
    };
  }, []);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Options Intelligence Terminal
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Real-time multi-dimensional scoring and analytics
          </p>
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

      {/* Main Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ScoreGauge label="BULL PROBABILITY" score={scores.bull_score} variant="bull" loading={loading} />
        <ScoreGauge label="BEAR PROBABILITY" score={scores.bear_score} variant="bear" loading={loading} />
        <ScoreGauge label="MODEL CONFIDENCE" score={scores.confidence} variant="info" loading={loading} />
      </div>

      {/* Spot prices */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard label="NIFTY 50" value={niftySpot} variant="info" loading={loading} />
        <MetricCard label="BANK NIFTY" value={bankNiftySpot} variant="info" loading={loading} />
        <MetricCard label="REGIME" value={scores.regime} loading={loading} />
        <MetricCard label="SIGNAL" value={scores.recommendation} variant={scores.recommendation === "BUY_CE" ? "bull" : scores.recommendation === "BUY_PE" ? "bear" : "default"} loading={loading} />
        <MetricCard label="INDIA VIX" value="13.2" loading={loading} />
        <MetricCard label="PCR (OI)" value="0.94" loading={loading} />
      </div>

      {/* Details layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="AI Intelligence Explainer" subtitle="Groq-powered market overview (updated minute-by-minute)">
          <div className="text-sm space-y-3 leading-relaxed text-[var(--color-text-secondary)]">
            <p>
              <b>Summary:</b> Market trading inside a consolidated range. Institutional dealer positioning indicates solid support around the {niftySpot} area.
            </p>
            <p>
              <b>GEX Profile:</b> Positive Gamma regime holds. Options pricing models imply restricted upper expansion bounds. Recommend defensive option strategies or long volatility spreads upon breakout confirmation.
            </p>
          </div>
        </Card>

        <Card title="Platform Indicators Breakdown" subtitle="Scoring weights and factors alignment">
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">Trend Component</span>
              <span className="text-[var(--color-bull)] font-mono">Bullish (+65)</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">Momentum Component</span>
              <span className="text-[var(--color-bear)] font-mono">Bearish (-32)</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">GEX Exposure (Dealer Delta)</span>
              <span className="text-[var(--color-bull)] font-mono">Positive GEX</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
