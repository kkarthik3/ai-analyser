"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getOptionChain, getOptionChainExpiries, getAnalyticsHistory, OptionChainRow } from "@/lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";

type Tab = "charts" | "trends" | "heatmap";

export default function OIHeatmapPage() {
  const [symbol, setSymbol] = useState("NSE:NIFTY50-INDEX");
  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<string>("");
  const [strikeRange, setStrikeRange] = useState<string>("12");
  const [activeTab, setActiveTab] = useState<Tab>("charts");

  const [chain, setChain] = useState<OptionChainRow[]>([]);
  const [history, setHistory] = useState<any[]>([]);
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

  // Fetch live option chain and historical analytics
  const fetchData = async () => {
    if (!selectedExpiry) return;
    try {
      const [chainResp, historyResp] = await Promise.all([
        getOptionChain(underlying, selectedExpiry),
        getAnalyticsHistory(underlying, selectedExpiry),
      ]);
      setChain(chainResp.data || []);
      setHistory(historyResp || []);
    } catch (err) {
      console.error("Failed to load analytics data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchData();
    const timer = setInterval(fetchData, 5000);
    return () => clearInterval(timer);
  }, [symbol, selectedExpiry]);

  // Unique sorted strikes
  const strikes = Array.from(new Set(chain.map((c) => c.strike))).sort((a, b) => a - b);
  const spotPrice = chain[0]?.spot_price || 0;

  // Find At-The-Money (ATM) Strike
  const atmStrike = strikes.reduce((prev, curr) =>
    Math.abs(curr - spotPrice) < Math.abs(prev - spotPrice) ? curr : prev
  , strikes[0]);

  const atmIndex = strikes.indexOf(atmStrike);

  // Filter strikes based on selected strike range centered around ATM
  let filteredStrikes = strikes;
  if (strikeRange !== "all" && strikes.length > 0) {
    const rangeCount = parseInt(strikeRange) || 12;
    const half = Math.floor(rangeCount / 2);
    const start = Math.max(0, atmIndex - half);
    const end = Math.min(strikes.length, atmIndex + half + 1);
    filteredStrikes = strikes.slice(start, end);
  }

  // Map option data for Recharts Bar Chart
  const barChartData = filteredStrikes.map((strike) => {
    const ce = chain.find((c) => c.strike === strike && c.option_type === "CE");
    const pe = chain.find((c) => c.strike === strike && c.option_type === "PE");
    return {
      strike: strike.toString(),
      "Call OI": ce?.oi || 0,
      "Put OI": pe?.oi || 0,
      "Call OI Chg": ce?.change_oi || 0,
      "Put OI Chg": pe?.change_oi || 0,
    };
  });

  // Map history data for Line Charts
  const lineChartData = history.map((h) => {
    const formattedTime = new Date(h.time).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    });
    return {
      ...h,
      timeLabel: formattedTime,
    };
  });

  const getBarWidth = (value: number, max: number) => {
    if (max <= 0) return "0%";
    return `${(value / max) * 100}%`;
  };

  const maxOI = Math.max(...chain.map((c) => c.oi || 1));
  const heatmapStrikes = Array.from(new Set(chain.map((c) => c.strike)))
    .sort((a, b) => b - a)
    .slice(0, 10);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header and Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Open Interest & Option Analytics
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Visualizing strike distribution, PCR dynamics, and historical Max Pain curves
          </p>
        </div>

        {/* Global Filters */}
        <div className="flex flex-wrap items-center gap-3 self-start lg:self-center">
          {/* Index Selector */}
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none font-semibold"
          >
            <option value="NSE:NIFTY50-INDEX">NIFTY 50</option>
            <option value="NSE:NIFTYBANK-INDEX">BANK NIFTY</option>
          </select>

          {/* Expiry Dropdown */}
          {expiries.length > 0 && (
            <select
              value={selectedExpiry}
              onChange={(e) => setSelectedExpiry(e.target.value)}
              className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none font-semibold"
            >
              {expiries.map((exp) => (
                <option key={exp} value={exp}>
                  Expiry: {exp}
                </option>
              ))}
            </select>
          )}

          {/* Strike Range Dropdown */}
          <select
            value={strikeRange}
            onChange={(e) => setStrikeRange(e.target.value)}
            className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:outline-none font-semibold"
          >
            <option value="6">Strike Range: 6 (ATM)</option>
            <option value="12">Strike Range: 12 (ATM)</option>
            <option value="20">Strike Range: 20 (ATM)</option>
            <option value="all">All Strikes</option>
          </select>

          {/* Tab Selection */}
          <div className="flex bg-[var(--color-bg-elevated)] p-1 rounded-lg border border-[var(--color-border)] font-semibold text-xs">
            <button
              onClick={() => setActiveTab("charts")}
              className={`px-3 py-1 rounded transition-all duration-200 ${
                activeTab === "charts"
                  ? "bg-[var(--color-bg-card)] text-[var(--color-text-primary)] shadow-sm"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
            >
              OI Distribution
            </button>
            <button
              onClick={() => setActiveTab("trends")}
              className={`px-3 py-1 rounded transition-all duration-200 ${
                activeTab === "trends"
                  ? "bg-[var(--color-bg-card)] text-[var(--color-text-primary)] shadow-sm"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
            >
              OI Trends
            </button>
            <button
              onClick={() => setActiveTab("heatmap")}
              className={`px-3 py-1 rounded transition-all duration-200 ${
                activeTab === "heatmap"
                  ? "bg-[var(--color-bg-card)] text-[var(--color-text-primary)] shadow-sm"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
            >
              Heatmap
            </button>
          </div>
        </div>
      </div>

      {loading && chain.length === 0 ? (
        <div className="flex justify-center items-center py-20 text-sm text-[var(--color-text-muted)]">
          Loading option statistics...
        </div>
      ) : chain.length === 0 ? (
        <div className="flex justify-center items-center py-20 text-sm text-[var(--color-text-muted)]">
          No options analytics data available. Ensure option chain poller is running.
        </div>
      ) : (
        <div className="space-y-4">
          {/* Subtitle Spot Indicator */}
          <div className="flex items-center gap-2 text-xs font-semibold bg-[var(--color-bg-elevated)] border border-[var(--color-border)] px-3 py-2 rounded-lg w-max font-mono shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] animate-pulse" />
            <span className="text-[var(--color-text-muted)]">SPOT PRICE:</span>
            <span className="text-[var(--color-text-primary)]">₹{spotPrice.toFixed(2)}</span>
            <span className="text-[var(--color-text-muted)] ml-2">ATM STRIKE:</span>
            <span className="text-[var(--color-accent)]">{atmStrike}</span>
          </div>

          {/* TAB 1: OI Distribution Charts */}
          {activeTab === "charts" && (
            <div className="grid grid-cols-1 gap-4">
              <Card
                title="Call & Put OI Change by Strike"
                subtitle="Visualizes real-time delta build-up (Red = Calls, Teal = Puts) showing key resistance and support lines"
              >
                <div className="w-full h-[340px] pt-4 font-mono text-[10px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barChartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#25262b" />
                      <XAxis dataKey="strike" stroke="#888" />
                      <YAxis stroke="#888" label={{ value: "Contracts Volume (OI Change)", angle: -90, position: "insideLeft", offset: 0, fill: "#888" }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1c1e22", border: "1px solid #333", borderRadius: 6 }}
                        labelStyle={{ fontWeight: "bold", color: "#fff" }}
                      />
                      <Legend verticalAlign="top" height={36} />
                      <ReferenceLine y={0} stroke="#666" strokeWidth={1} />
                      <Bar dataKey="Call OI Chg" name="Call OI Change" fill="var(--color-bear)" radius={[3, 3, 0, 0]} />
                      <Bar dataKey="Put OI Chg" name="Put OI Change" fill="var(--color-bull)" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card
                title="Total Open Interest (OI) Distribution"
                subtitle="Grouped call and put open contracts per strike"
              >
                <div className="w-full h-[340px] pt-4 font-mono text-[10px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barChartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#25262b" />
                      <XAxis dataKey="strike" stroke="#888" />
                      <YAxis stroke="#888" label={{ value: "Total Open Interest (Contracts)", angle: -90, position: "insideLeft", offset: 0, fill: "#888" }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1c1e22", border: "1px solid #333", borderRadius: 6 }}
                        labelStyle={{ fontWeight: "bold", color: "#fff" }}
                      />
                      <Legend verticalAlign="top" height={36} />
                      <Bar dataKey="Call OI" name="Call Total OI" fill="var(--color-bear)" radius={[3, 3, 0, 0]} />
                      <Bar dataKey="Put OI" name="Put Total OI" fill="var(--color-bull)" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {/* TAB 2: Historical OI Trends */}
          {activeTab === "trends" && (
            history.length === 0 ? (
              <div className="flex justify-center items-center py-20 text-sm text-[var(--color-text-muted)] bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg">
                No historical trend data recorded in the database yet. Collecting ticks...
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card title="Put-Call Ratio (PCR)" subtitle="Time vs PCR dynamic index curve (Sentiment Indicator)">
                  <div className="w-full h-[260px] pt-4 font-mono text-[10px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={lineChartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#25262b" />
                        <XAxis dataKey="timeLabel" stroke="#888" />
                        <YAxis stroke="#888" domain={["auto", "auto"]} />
                        <Tooltip contentStyle={{ backgroundColor: "#1c1e22", border: "1px solid #333", borderRadius: 6 }} />
                        <Legend />
                        <Line type="monotone" dataKey="pcr" name="PCR Index" stroke="var(--color-info)" strokeWidth={2} dot={false} />
                        <ReferenceLine y={1.0} stroke="#666" strokeDasharray="3 3" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                <Card title="Max Pain vs Spot Price" subtitle="Comparing option buyer pain minimization strike with spot price">
                  <div className="w-full h-[260px] pt-4 font-mono text-[10px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={lineChartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#25262b" />
                        <XAxis dataKey="timeLabel" stroke="#888" />
                        <YAxis stroke="#888" domain={["auto", "auto"]} />
                        <Tooltip contentStyle={{ backgroundColor: "#1c1e22", border: "1px solid #333", borderRadius: 6 }} />
                        <Legend />
                        <Line type="monotone" dataKey="max_pain" name="Max Pain Strike" stroke="var(--color-accent)" strokeWidth={2.5} dot={true} />
                        <Line type="monotone" dataKey="spot_price" name="Spot Price" stroke="#fff" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                <Card title="Total Call/Put OI Buildup" subtitle="Buildup of market volumes over time">
                  <div className="w-full h-[260px] pt-4 font-mono text-[10px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={lineChartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#25262b" />
                        <XAxis dataKey="timeLabel" stroke="#888" />
                        <YAxis stroke="#888" />
                        <Tooltip contentStyle={{ backgroundColor: "#1c1e22", border: "1px solid #333", borderRadius: 6 }} />
                        <Legend />
                        <Line type="monotone" dataKey="total_call_oi" name="Total Call OI" stroke="var(--color-bear)" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="total_put_oi" name="Total Put OI" stroke="var(--color-bull)" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>
            )
          )}

          {/* TAB 3: Original Upgraded Heatmap Concentration */}
          {activeTab === "heatmap" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Call concentration */}
              <Card title="Call Open Interest (CE)" subtitle={`Top strike concentration for expiry ${selectedExpiry}`}>
                <div className="space-y-3 font-mono">
                  {heatmapStrikes.map((strike) => {
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
              <Card title="Put Open Interest (PE)" subtitle={`Top strike concentration for expiry ${selectedExpiry}`}>
                <div className="space-y-3 font-mono">
                  {heatmapStrikes.map((strike) => {
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
          )}
        </div>
      )}
    </div>
  );
}
