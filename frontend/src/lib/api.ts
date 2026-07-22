/**
 * API client for communicating with the FastAPI backend.
 *
 * Provides typed, async methods for all REST endpoints with
 * error handling and base URL configuration.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    throw new ApiError(res.status, `API error: ${res.statusText}`);
  }

  return res.json();
}

// ---- Health ----

export async function getHealth() {
  return fetchApi<{
    status: string;
    timestamp: string;
    version: string;
    environment: string;
  }>("/api/v1/health");
}

export async function getSystemStatus() {
  return fetchApi<{
    status: string;
    timestamp: string;
    services: Record<string, unknown>;
    config: Record<string, unknown>;
  }>("/api/v1/status");
}

// ---- Auth ----

export async function getAuthUrl() {
  return fetchApi<{ auth_url: string; instructions: string }>(
    "/api/v1/auth/login"
  );
}

export async function getAuthStatus() {
  return fetchApi<{
    authenticated: boolean;
    token_preview: string | null;
    expires_at: string | null;
    has_refresh_token: boolean;
  }>("/api/v1/auth/status");
}

// ---- Market Data ----

export async function getLatestTicks(symbols?: string) {
  const params = symbols ? `?symbols=${symbols}` : "";
  return fetchApi<{
    data: Record<string, Record<string, unknown>>;
    count: number;
  }>(`/api/v1/market/ticks/latest${params}`);
}

export async function getOptionChain(underlying: string, expiry?: string) {
  const params = expiry ? `?expiry=${expiry}` : "";
  return fetchApi<{
    source: string;
    underlying: string;
    data: OptionChainRow[];
    count: number;
  }>(`/api/v1/market/option-chain/${underlying}${params}`);
}

export async function getComputedMetrics(symbol: string) {
  return fetchApi<{
    symbol: string;
    metrics: Record<string, number>;
  }>(`/api/v1/market/metrics/${symbol}`);
}

export async function getScores(symbol: string) {
  return fetchApi<{
    symbol: string;
    scores: Record<string, unknown>;
  }>(`/api/v1/market/scores/${symbol}`);
}

export async function getPositions() {
  return fetchApi<{
    s: string;
    netPositions?: any[];
    overall?: any;
    overallPosition?: any;
    message?: string;
  }>("/api/v1/market/portfolio/positions");
}

export async function getHoldings() {
  return fetchApi<{
    s: string;
    holdings?: any[];
    overall?: any;
    message?: string;
  }>("/api/v1/market/portfolio/holdings");
}

export async function getTradeJournal() {
  return fetchApi<any[]>("/api/v1/market/portfolio/journal");
}

export async function getTradeAnalytics() {
  return fetchApi<{
    win_rate: number;
    profit_factor: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    max_drawdown: number;
    trade_count: number;
  }>("/api/v1/market/portfolio/analytics");
}

export async function getProfile() {
  return fetchApi<{
    s: string;
    data?: any;
    message?: string;
  }>("/api/v1/market/portfolio/profile");
}

export async function getFunds() {
  return fetchApi<{
    s: string;
    fund_limit?: any[];
    message?: string;
  }>("/api/v1/market/portfolio/funds");
}

export async function getAIReport(symbol: string) {
  return fetchApi<{
    symbol: string;
    content: string | null;
    time?: string;
    model?: string;
    message?: string;
  }>(`/api/v1/market/ai-report/${symbol}`);
}

// ---- Types ----

export interface OptionChainRow {
  strike: number;
  option_type: "CE" | "PE";
  ltp: number;
  bid: number;
  ask: number;
  volume: number;
  oi: number;
  change_oi: number;
  iv: number | null;
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  vega: number | null;
  intrinsic_value: number | null;
  time_value: number | null;
  spot_price: number;
  time: string;
}

export interface TickData {
  symbol: string;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  bid: number;
  ask: number;
  oi: number;
  change_pct: number;
  received_at: string;
}

export interface ScoreData {
  bull_score: number;
  bear_score: number;
  confidence: number;
  trend_score: number;
  momentum_score: number;
  oi_score: number;
  greeks_score: number;
  volatility_score: number;
  structure_score: number;
  regime: string;
  recommendation: string;
}

export async function getOptionChainExpiries(underlying: string) {
  return fetchApi<string[]>(`/api/v1/market/option-chain/${underlying}/expiries`);
}

export async function getAnalyticsHistory(underlying: string, expiry?: string) {
  const params = expiry ? `?expiry=${expiry}` : "";
  return fetchApi<any[]>(`/api/v1/market/option-chain/${underlying}/analytics-history${params}`);
}
