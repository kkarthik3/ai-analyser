"use client";

import clsx from "clsx";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  variant?: "bull" | "bear" | "info";
  className?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  variant = "info",
  className,
}: SparklineProps) {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min === 0 ? 1 : max - min;

  const points = data
    .map((val, index) => {
      const x = (index / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  const colorVar =
    variant === "bull"
      ? "var(--color-bull)"
      : variant === "bear"
      ? "var(--color-bear)"
      : "var(--color-info)";

  return (
    <svg
      width={width}
      height={height}
      className={clsx("overflow-visible", className)}
    >
      <polyline
        fill="none"
        stroke={colorVar}
        strokeWidth="1.5"
        points={points}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
