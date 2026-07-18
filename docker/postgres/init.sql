-- ============================================================
-- AI-Bot Options Intelligence Platform
-- PostgreSQL + TimescaleDB Initialization
-- ============================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Instruments (reference table — standard PostgreSQL)
-- ============================================================
CREATE TABLE IF NOT EXISTS instruments (
    id              SERIAL PRIMARY KEY,
    symbol          TEXT NOT NULL UNIQUE,
    exchange        TEXT NOT NULL DEFAULT 'NSE',
    instrument_type TEXT NOT NULL DEFAULT 'INDEX',  -- INDEX, EQ, CE, PE, FUT
    name            TEXT,
    lot_size        INTEGER DEFAULT 1,
    tick_size       DOUBLE PRECISION DEFAULT 0.05,
    expiry          DATE,
    strike          DOUBLE PRECISION,
    underlying      TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_underlying ON instruments(underlying);
CREATE INDEX IF NOT EXISTS idx_instruments_type ON instruments(instrument_type);

-- ============================================================
-- Market Ticks (hypertable)
-- ============================================================
CREATE TABLE IF NOT EXISTS market_ticks (
    time            TIMESTAMPTZ NOT NULL,
    instrument_id   INTEGER NOT NULL REFERENCES instruments(id),
    symbol          TEXT NOT NULL,
    ltp             DOUBLE PRECISION,
    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    close           DOUBLE PRECISION,
    bid             DOUBLE PRECISION,
    ask             DOUBLE PRECISION,
    bid_qty         BIGINT,
    ask_qty         BIGINT,
    volume          BIGINT,
    oi              BIGINT DEFAULT 0,
    change_oi       DOUBLE PRECISION DEFAULT 0,
    prev_close      DOUBLE PRECISION,
    change_pct      DOUBLE PRECISION
);

SELECT create_hypertable('market_ticks', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON market_ticks(symbol, time DESC);

-- ============================================================
-- Option Chain Snapshots (hypertable)
-- ============================================================
CREATE TABLE IF NOT EXISTS option_chain_snapshots (
    time            TIMESTAMPTZ NOT NULL,
    underlying      TEXT NOT NULL,
    expiry          DATE NOT NULL,
    strike          DOUBLE PRECISION NOT NULL,
    option_type     TEXT NOT NULL,  -- CE or PE
    symbol          TEXT NOT NULL,
    ltp             DOUBLE PRECISION,
    bid             DOUBLE PRECISION,
    ask             DOUBLE PRECISION,
    bid_qty         BIGINT,
    ask_qty         BIGINT,
    volume          BIGINT DEFAULT 0,
    oi              BIGINT DEFAULT 0,
    change_oi       DOUBLE PRECISION DEFAULT 0,
    iv              DOUBLE PRECISION,
    delta           DOUBLE PRECISION,
    gamma           DOUBLE PRECISION,
    theta           DOUBLE PRECISION,
    vega            DOUBLE PRECISION,
    rho             DOUBLE PRECISION,
    intrinsic_value DOUBLE PRECISION,
    time_value      DOUBLE PRECISION,
    spot_price      DOUBLE PRECISION
);

SELECT create_hypertable('option_chain_snapshots', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_chain_underlying_time
    ON option_chain_snapshots(underlying, time DESC);
CREATE INDEX IF NOT EXISTS idx_chain_strike_type
    ON option_chain_snapshots(underlying, strike, option_type, time DESC);

-- ============================================================
-- Computed Metrics (hypertable)
-- ============================================================
CREATE TABLE IF NOT EXISTS computed_metrics (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    value           DOUBLE PRECISION,
    metadata        JSONB DEFAULT '{}'
);

SELECT create_hypertable('computed_metrics', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_metrics_symbol_name_time
    ON computed_metrics(symbol, metric_name, time DESC);

-- ============================================================
-- Feature Store (hypertable)
-- ============================================================
CREATE TABLE IF NOT EXISTS feature_store (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL,
    features        JSONB NOT NULL
);

SELECT create_hypertable('feature_store', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_features_symbol_time
    ON feature_store(symbol, time DESC);

-- ============================================================
-- Scoring Snapshots (hypertable)
-- ============================================================
CREATE TABLE IF NOT EXISTS scoring_snapshots (
    time              TIMESTAMPTZ NOT NULL,
    symbol            TEXT NOT NULL,
    bull_score        DOUBLE PRECISION,
    bear_score        DOUBLE PRECISION,
    confidence        DOUBLE PRECISION,
    trend_score       DOUBLE PRECISION,
    momentum_score    DOUBLE PRECISION,
    oi_score          DOUBLE PRECISION,
    greeks_score      DOUBLE PRECISION,
    volatility_score  DOUBLE PRECISION,
    structure_score   DOUBLE PRECISION,
    liquidity_score   DOUBLE PRECISION,
    risk_score        DOUBLE PRECISION,
    institutional_score DOUBLE PRECISION,
    dealer_score      DOUBLE PRECISION,
    regime            TEXT,
    recommendation    TEXT,
    metadata          JSONB DEFAULT '{}'
);

SELECT create_hypertable('scoring_snapshots', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_scores_symbol_time
    ON scoring_snapshots(symbol, time DESC);

-- ============================================================
-- Trade Signals
-- ============================================================
CREATE TABLE IF NOT EXISTS trade_signals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    symbol          TEXT NOT NULL,
    underlying      TEXT NOT NULL,
    direction       TEXT NOT NULL,         -- BUY_CE, BUY_PE, NO_TRADE
    status          TEXT DEFAULT 'ACTIVE', -- ACTIVE, EXECUTED, EXPIRED, CANCELLED
    entry_price     DOUBLE PRECISION,
    target_price    DOUBLE PRECISION,
    stop_loss       DOUBLE PRECISION,
    confidence      DOUBLE PRECISION,
    bull_score      DOUBLE PRECISION,
    bear_score      DOUBLE PRECISION,
    risk_reward     DOUBLE PRECISION,
    reasoning       JSONB DEFAULT '{}',
    factors         JSONB DEFAULT '{}',
    market_snapshot JSONB DEFAULT '{}',
    expires_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_signals_status ON trade_signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trade_signals(symbol, created_at DESC);

-- ============================================================
-- Trade Journal
-- ============================================================
CREATE TABLE IF NOT EXISTS trade_journal (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id       UUID REFERENCES trade_signals(id),
    symbol          TEXT NOT NULL,
    direction       TEXT NOT NULL,
    entry_time      TIMESTAMPTZ NOT NULL,
    exit_time       TIMESTAMPTZ,
    entry_price     DOUBLE PRECISION NOT NULL,
    exit_price      DOUBLE PRECISION,
    quantity        INTEGER DEFAULT 1,
    pnl             DOUBLE PRECISION,
    pnl_pct         DOUBLE PRECISION,
    exit_reason     TEXT,
    entry_snapshot  JSONB DEFAULT '{}',
    exit_snapshot   JSONB DEFAULT '{}',
    greeks_at_entry JSONB DEFAULT '{}',
    greeks_at_exit  JSONB DEFAULT '{}',
    scores_at_entry JSONB DEFAULT '{}',
    lessons         JSONB DEFAULT '{}',
    ai_analysis     TEXT,
    tags            TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_symbol ON trade_journal(symbol, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_journal_pnl ON trade_journal(pnl);

-- ============================================================
-- ML Predictions (hypertable)
-- ============================================================
CREATE TABLE IF NOT EXISTS ml_predictions (
    time              TIMESTAMPTZ NOT NULL,
    symbol            TEXT NOT NULL,
    model_name        TEXT NOT NULL,
    model_version     TEXT,
    prob_gain_10pct   DOUBLE PRECISION,
    prob_gain_20pct   DOUBLE PRECISION,
    prob_gain_30pct   DOUBLE PRECISION,
    horizon_minutes   INTEGER,
    feature_importance JSONB DEFAULT '{}',
    metadata          JSONB DEFAULT '{}'
);

SELECT create_hypertable('ml_predictions', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_ml_symbol_time
    ON ml_predictions(symbol, model_name, time DESC);

-- ============================================================
-- AI Reports
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    symbol          TEXT NOT NULL,
    report_type     TEXT NOT NULL,  -- MARKET_ANALYSIS, TRADE_EXPLANATION, EXIT_ANALYSIS, LEARNING
    content         TEXT NOT NULL,
    metrics_referenced JSONB DEFAULT '{}',
    scores_snapshot JSONB DEFAULT '{}',
    model_used      TEXT,
    prompt_tokens   INTEGER,
    completion_tokens INTEGER
);

CREATE INDEX IF NOT EXISTS idx_reports_symbol_time
    ON ai_reports(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_type
    ON ai_reports(report_type, created_at DESC);

-- ============================================================
-- Compression Policies (for older data)
-- ============================================================
ALTER TABLE market_ticks SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

ALTER TABLE option_chain_snapshots SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'underlying, strike, option_type'
);

ALTER TABLE computed_metrics SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'symbol, metric_name'
);

ALTER TABLE feature_store SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'symbol'
);

-- Auto-compress chunks older than 7 days
SELECT add_compression_policy('market_ticks', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('option_chain_snapshots', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('computed_metrics', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('feature_store', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================================
-- Continuous Aggregates — 1-minute OHLCV
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    FIRST(ltp, time) AS open,
    MAX(ltp) AS high,
    MIN(ltp) AS low,
    LAST(ltp, time) AS close,
    SUM(volume) AS volume,
    LAST(oi, time) AS oi
FROM market_ticks
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('ohlcv_1m',
    start_offset    => INTERVAL '1 hour',
    end_offset      => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists   => TRUE
);
