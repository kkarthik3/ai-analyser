"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";

type SystemStatus = "connected" | "disconnected" | "connecting";

export function TopBar() {
  const [time, setTime] = useState<string>("");
  const [status, setStatus] = useState<SystemStatus>("disconnected");
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "Asia/Kolkata",
        })
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Check API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/v1/health`);
        if (res.ok) {
          setStatus("connected");
        } else {
          setStatus("disconnected");
        }
      } catch {
        setStatus("disconnected");
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const isMarketHours = () => {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentMinutes = hours * 60 + minutes;
    // NSE: 9:15 AM to 3:30 PM IST
    return currentMinutes >= 555 && currentMinutes <= 930;
  };

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b bg-[var(--color-bg-secondary)] border-[var(--color-border)]">
      {/* Left: Market Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <StatusDot status={isMarketHours() ? "active" : "inactive"} />
          <span className="text-xs font-medium text-[var(--color-text-secondary)]">
            {isMarketHours() ? "MARKET OPEN" : "MARKET CLOSED"}
          </span>
        </div>

        <div className="h-4 w-px bg-[var(--color-border)]" />

        <div className="flex items-center gap-2">
          <StatusDot
            status={
              status === "connected"
                ? "active"
                : status === "connecting"
                ? "warning"
                : "inactive"
            }
          />
          <span className="text-xs text-[var(--color-text-muted)]">
            API: {status}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <StatusDot status={wsConnected ? "active" : "inactive"} />
          <span className="text-xs text-[var(--color-text-muted)]">
            WS: {wsConnected ? "live" : "off"}
          </span>
        </div>
      </div>

      {/* Right: Clock */}
      <div className="flex items-center gap-4">
        <span className="text-xs text-[var(--color-text-muted)]">IST</span>
        <span className="text-sm font-mono font-semibold text-[var(--color-text-primary)] tabular-nums">
          {time}
        </span>
      </div>
    </header>
  );
}

function StatusDot({ status }: { status: "active" | "warning" | "inactive" }) {
  return (
    <span className="relative flex h-2 w-2">
      {status === "active" && (
        <span className="absolute inline-flex h-full w-full rounded-full bg-[var(--color-bull)] opacity-75 animate-ping" />
      )}
      <span
        className={clsx(
          "relative inline-flex rounded-full h-2 w-2",
          status === "active" && "bg-[var(--color-bull)]",
          status === "warning" && "bg-[var(--color-neutral)]",
          status === "inactive" && "bg-[var(--color-text-muted)]"
        )}
      />
    </span>
  );
}
