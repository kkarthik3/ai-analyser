"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

interface ScoreGaugeProps {
  label: string;
  score: number;
  variant?: "bull" | "bear" | "info" | "neutral";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export function ScoreGauge({
  label,
  score,
  variant = "info",
  size = "md",
  loading = false,
}: ScoreGaugeProps) {
  const colorVar =
    variant === "bull"
      ? "var(--color-bull)"
      : variant === "bear"
      ? "var(--color-bear)"
      : variant === "neutral"
      ? "var(--color-neutral)"
      : "var(--color-info)";

  const dimVar =
    variant === "bull"
      ? "var(--color-bull-dim)"
      : variant === "bear"
      ? "var(--color-bear-dim)"
      : variant === "neutral"
      ? "var(--color-neutral-dim)"
      : "var(--color-info-dim)";

  const dimensions =
    size === "sm" ? "w-16 h-16" : size === "md" ? "w-24 h-24" : "w-32 h-32";

  const strokeWidth = size === "sm" ? 6 : size === "md" ? 8 : 10;
  const radius = size === "sm" ? 26 : size === "md" ? 42 : 54;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className="flex flex-col items-center">
      <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)] mb-2">
        {label}
      </span>

      {loading ? (
        <div className={clsx("rounded-full bg-[var(--color-bg-elevated)] animate-pulse", dimensions)} />
      ) : (
        <div className={clsx("relative", dimensions)}>
          <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke={dimVar}
              strokeWidth={strokeWidth}
            />
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke={colorVar}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={`${(score / 100) * circumference} ${circumference}`}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className={clsx(
                "font-bold tabular-nums",
                size === "sm" ? "text-sm" : size === "md" ? "text-xl" : "text-3xl"
              )}
              style={{ color: colorVar }}
            >
              {score}
            </span>
            <span className="text-[9px] text-[var(--color-text-muted)] -mt-1">%</span>
          </div>
        </div>
      )}
    </div>
  );
}
