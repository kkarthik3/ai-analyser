"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number;
  suffix?: string;
  prefix?: string;
  variant?: "default" | "bull" | "bear" | "info" | "accent";
  size?: "sm" | "md" | "lg";
  sparkline?: number[];
  loading?: boolean;
}

export function MetricCard({
  label,
  value,
  change,
  suffix,
  prefix,
  variant = "default",
  size = "md",
  loading = false,
}: MetricCardProps) {
  const changeColor =
    change !== undefined
      ? change > 0
        ? "text-[var(--color-bull)]"
        : change < 0
        ? "text-[var(--color-bear)]"
        : "text-[var(--color-text-muted)]"
      : "";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={clsx(
        "glass-card p-3 flex flex-col gap-1",
        variant === "bull" && "border-l-2 border-l-[var(--color-bull)]",
        variant === "bear" && "border-l-2 border-l-[var(--color-bear)]",
        variant === "info" && "border-l-2 border-l-[var(--color-info)]",
        variant === "accent" && "border-l-2 border-l-[var(--color-accent)]"
      )}
    >
      <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-muted)] font-medium">
        {label}
      </span>

      {loading ? (
        <div className="h-6 w-20 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
      ) : (
        <div className="flex items-baseline gap-1">
          {prefix && (
            <span className="text-xs text-[var(--color-text-muted)]">{prefix}</span>
          )}
          <span
            className={clsx(
              "font-bold tabular-nums",
              size === "sm" && "text-base",
              size === "md" && "text-xl",
              size === "lg" && "text-2xl",
              variant === "bull" && "text-[var(--color-bull)]",
              variant === "bear" && "text-[var(--color-bear)]",
              variant === "info" && "text-[var(--color-info)]",
              variant === "accent" && "text-[var(--color-accent)]",
              variant === "default" && "text-[var(--color-text-primary)]"
            )}
          >
            {typeof value === "number" ? value.toLocaleString() : value}
          </span>
          {suffix && (
            <span className="text-xs text-[var(--color-text-muted)]">{suffix}</span>
          )}
        </div>
      )}

      {change !== undefined && !loading && (
        <div className={clsx("flex items-center gap-1 text-xs", changeColor)}>
          <span>{change > 0 ? "▲" : change < 0 ? "▼" : "—"}</span>
          <span className="font-medium tabular-nums">
            {Math.abs(change).toFixed(2)}%
          </span>
        </div>
      )}
    </motion.div>
  );
}
