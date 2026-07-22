"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

const NAV_ITEMS = [
  {
    label: "Dashboard",
    href: "/",
    icon: "📊",
    description: "Scores & Overview",
  },
  {
    label: "Option Chain",
    href: "/option-chain",
    icon: "⛓️",
    description: "Live Chain + Greeks",
  },
  {
    label: "OI Heatmap",
    href: "/oi-heatmap",
    icon: "🗺️",
    description: "Open Interest Analysis",
  },
  {
    label: "Greeks",
    href: "/greeks",
    icon: "Δ",
    description: "Greeks & IV Surface",
  },
  {
    label: "Watchlist Tickers",
    href: "/breadth",
    icon: "📈",
    description: "Watchlist Momentum & LTPs",
  },
  {
    label: "Trade Monitor",
    href: "/trades",
    icon: "🎯",
    description: "Active Trades & Exits",
  },
  {
    label: "Analytics",
    href: "/analytics",
    icon: "📉",
    description: "Journal & Performance",
  },
  {
    label: "Replay",
    href: "/replay",
    icon: "⏪",
    description: "Backtest & Replay",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 64 : 220 }}
      transition={{ duration: 0.2 }}
      className={clsx(
        "flex flex-col border-r h-full",
        "bg-[var(--color-bg-secondary)] border-[var(--color-border)]"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-[var(--color-border)]">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
          AI
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="text-sm font-semibold text-[var(--color-text-primary)] whitespace-nowrap">
                Options Intel
              </div>
              <div className="text-[10px] text-[var(--color-text-muted)] whitespace-nowrap">
                AI-Powered Platform
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link key={item.href} href={item.href}>
              <div
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 cursor-pointer group",
                  isActive
                    ? "bg-[var(--color-info-dim)] text-[var(--color-text-accent)] border border-[var(--color-border-focus)]/20"
                    : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card)] hover:text-[var(--color-text-primary)]"
                )}
              >
                <span className="text-lg shrink-0 w-6 text-center">{item.icon}</span>
                <AnimatePresence>
                  {!collapsed && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="text-sm font-medium whitespace-nowrap">{item.label}</div>
                      <div className="text-[10px] text-[var(--color-text-muted)] whitespace-nowrap">
                        {item.description}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center py-3 border-t border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
      >
        <span className="text-sm">{collapsed ? "»" : "«"}</span>
      </button>
    </motion.aside>
  );
}
