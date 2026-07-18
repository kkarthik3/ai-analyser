"use client";

import clsx from "clsx";

interface StatusIndicatorProps {
  status: "connected" | "disconnected" | "warning" | "loading";
  label?: string;
  size?: "sm" | "md" | "lg";
}

export function StatusIndicator({
  status,
  label,
  size = "sm",
}: StatusIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="relative flex">
        {(status === "connected" || status === "loading") && (
          <span
            className={clsx(
              "absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping",
              status === "connected" && "bg-[var(--color-bull)]",
              status === "loading" && "bg-[var(--color-neutral)]"
            )}
            style={{
              width: size === "sm" ? 8 : size === "md" ? 10 : 12,
              height: size === "sm" ? 8 : size === "md" ? 10 : 12,
            }}
          />
        )}
        <span
          className={clsx(
            "relative inline-flex rounded-full",
            status === "connected" && "bg-[var(--color-bull)]",
            status === "disconnected" && "bg-[var(--color-bear)]",
            status === "warning" && "bg-[var(--color-neutral)]",
            status === "loading" && "bg-[var(--color-neutral)]"
          )}
          style={{
            width: size === "sm" ? 8 : size === "md" ? 10 : 12,
            height: size === "sm" ? 8 : size === "md" ? 10 : 12,
          }}
        />
      </span>
      {label && (
        <span
          className={clsx(
            "font-medium",
            size === "sm" && "text-xs",
            size === "md" && "text-sm",
            size === "lg" && "text-base",
            "text-[var(--color-text-secondary)]"
          )}
        >
          {label}
        </span>
      )}
    </div>
  );
}
