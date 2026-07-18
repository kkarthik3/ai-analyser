"use client";

import { motion } from "framer-motion";
import clsx from "clsx";
import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hoverable?: boolean;
  glow?: "bull" | "bear" | "info" | "accent" | null;
  animate?: boolean;
  title?: string;
  subtitle?: string;
  headerRight?: ReactNode;
}

export function Card({
  children,
  className,
  hoverable = false,
  glow = null,
  animate = true,
  title,
  subtitle,
  headerRight,
}: CardProps) {
  const Wrapper = animate ? motion.div : "div";
  const animateProps = animate
    ? { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.3 } }
    : {};

  return (
    <Wrapper
      {...animateProps}
      className={clsx(
        "glass-card p-4",
        hoverable && "glass-card-hover cursor-pointer",
        glow === "bull" && "ring-1 ring-[var(--color-bull)]/20",
        glow === "bear" && "ring-1 ring-[var(--color-bear)]/20",
        glow === "info" && "ring-1 ring-[var(--color-info)]/20",
        glow === "accent" && "ring-1 ring-[var(--color-accent)]/20",
        className
      )}
    >
      {(title || headerRight) && (
        <div className="flex items-center justify-between mb-3">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {headerRight}
        </div>
      )}
      {children}
    </Wrapper>
  );
}
