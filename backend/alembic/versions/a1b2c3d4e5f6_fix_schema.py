"""fix schema: composite PKs, hypertables, indexes, FK on journal signal_id

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-07-20 00:53:00.000000

Changes from initial migration:
- All time-series tables now have composite primary keys (time is NOT unique alone)
- All 6 hypertables are converted via create_hypertable()
- server_default added to market_ticks.oi and change_oi
- FK added from trade_journal.signal_id → trade_signals.id
- exit_snapshot and greeks_at_exit made nullable in trade_journal
- Critical indexes added for all high-traffic query paths
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────
    # 1. Instruments (standard table — unchanged structure, keep indexes)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'instruments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('exchange', sa.String(length=10), nullable=False),
        sa.Column('instrument_type', sa.String(length=10), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('lot_size', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('tick_size', sa.Float(), nullable=False, server_default='0.05'),
        sa.Column('expiry', sa.Date(), nullable=True),
        sa.Column('strike', sa.Float(), nullable=True),
        sa.Column('underlying', sa.String(length=100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_instruments_symbol'), 'instruments', ['symbol'], unique=True)
    op.create_index(op.f('ix_instruments_underlying'), 'instruments', ['underlying'], unique=False)

    # ─────────────────────────────────────────────────────────────────────
    # 2. market_ticks — composite PK (time, symbol) + hypertable
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'market_ticks',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('ltp', sa.Float(), nullable=True),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('close', sa.Float(), nullable=True),
        sa.Column('bid', sa.Float(), nullable=True),
        sa.Column('ask', sa.Float(), nullable=True),
        sa.Column('bid_qty', sa.BigInteger(), nullable=True),
        sa.Column('ask_qty', sa.BigInteger(), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('oi', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('change_oi', sa.Float(), nullable=False, server_default='0'),
        sa.Column('prev_close', sa.Float(), nullable=True),
        sa.Column('change_pct', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id']),
        sa.PrimaryKeyConstraint('time', 'symbol', name='pk_market_ticks'),
    )
    # Convert to TimescaleDB hypertable partitioned by time
    op.execute(
        "SELECT create_hypertable('market_ticks', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    # Query indexes
    op.create_index('ix_market_ticks_symbol_time', 'market_ticks', ['symbol', sa.text('time DESC')])
    op.create_index('ix_market_ticks_instrument_id', 'market_ticks', ['instrument_id'])

    # ─────────────────────────────────────────────────────────────────────
    # 3. option_chain_snapshots — composite PK + hypertable
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'option_chain_snapshots',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('underlying', sa.String(length=50), nullable=False),
        sa.Column('expiry', sa.Date(), nullable=False),
        sa.Column('strike', sa.Float(), nullable=False),
        sa.Column('option_type', sa.String(length=2), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('ltp', sa.Float(), nullable=True),
        sa.Column('bid', sa.Float(), nullable=True),
        sa.Column('ask', sa.Float(), nullable=True),
        sa.Column('bid_qty', sa.BigInteger(), nullable=True),
        sa.Column('ask_qty', sa.BigInteger(), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('oi', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('change_oi', sa.Float(), nullable=False, server_default='0'),
        sa.Column('iv', sa.Float(), nullable=True),
        sa.Column('delta', sa.Float(), nullable=True),
        sa.Column('gamma', sa.Float(), nullable=True),
        sa.Column('theta', sa.Float(), nullable=True),
        sa.Column('vega', sa.Float(), nullable=True),
        sa.Column('rho', sa.Float(), nullable=True),
        sa.Column('intrinsic_value', sa.Float(), nullable=True),
        sa.Column('time_value', sa.Float(), nullable=True),
        sa.Column('spot_price', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('time', 'underlying', 'strike', 'option_type', name='pk_option_chain_snapshots'),
    )
    op.execute(
        "SELECT create_hypertable('option_chain_snapshots', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    # Most common query patterns
    op.create_index('ix_ocs_underlying_time', 'option_chain_snapshots', ['underlying', sa.text('time DESC')])
    op.create_index('ix_ocs_underlying_strike_type_time', 'option_chain_snapshots',
                    ['underlying', 'strike', 'option_type', 'time'])

    # ─────────────────────────────────────────────────────────────────────
    # 4. computed_metrics — composite PK + hypertable
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'computed_metrics',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('time', 'symbol', 'metric_name', name='pk_computed_metrics'),
    )
    op.execute(
        "SELECT create_hypertable('computed_metrics', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.create_index('ix_computed_metrics_symbol_metric_time', 'computed_metrics',
                    ['symbol', 'metric_name', sa.text('time DESC')])

    # ─────────────────────────────────────────────────────────────────────
    # 5. feature_store — composite PK + hypertable
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'feature_store',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('time', 'symbol', name='pk_feature_store'),
    )
    op.execute(
        "SELECT create_hypertable('feature_store', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.create_index('ix_feature_store_symbol_time', 'feature_store', ['symbol', sa.text('time DESC')])

    # ─────────────────────────────────────────────────────────────────────
    # 6. ml_predictions — composite PK + hypertable
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'ml_predictions',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('model_name', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.Column('prob_gain_10pct', sa.Float(), nullable=True),
        sa.Column('prob_gain_20pct', sa.Float(), nullable=True),
        sa.Column('prob_gain_30pct', sa.Float(), nullable=True),
        sa.Column('horizon_minutes', sa.Integer(), nullable=True),
        sa.Column('feature_importance', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('time', 'symbol', 'model_name', name='pk_ml_predictions'),
    )
    op.execute(
        "SELECT create_hypertable('ml_predictions', 'time', "
        "chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)"
    )
    op.create_index('ix_ml_predictions_symbol_model_time', 'ml_predictions',
                    ['symbol', 'model_name', sa.text('time DESC')])

    # ─────────────────────────────────────────────────────────────────────
    # 7. scoring_snapshots — composite PK + hypertable
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'scoring_snapshots',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('bull_score', sa.Float(), nullable=True),
        sa.Column('bear_score', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('trend_score', sa.Float(), nullable=True),
        sa.Column('momentum_score', sa.Float(), nullable=True),
        sa.Column('oi_score', sa.Float(), nullable=True),
        sa.Column('greeks_score', sa.Float(), nullable=True),
        sa.Column('volatility_score', sa.Float(), nullable=True),
        sa.Column('structure_score', sa.Float(), nullable=True),
        sa.Column('liquidity_score', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('institutional_score', sa.Float(), nullable=True),
        sa.Column('dealer_score', sa.Float(), nullable=True),
        sa.Column('regime', sa.String(length=50), nullable=True),
        sa.Column('recommendation', sa.String(length=20), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('time', 'symbol', name='pk_scoring_snapshots'),
    )
    op.execute(
        "SELECT create_hypertable('scoring_snapshots', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.create_index('ix_scoring_snapshots_symbol_time', 'scoring_snapshots',
                    ['symbol', sa.text('time DESC')])

    # ─────────────────────────────────────────────────────────────────────
    # 8. ai_reports
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'ai_reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('report_type', sa.String(length=30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metrics_referenced', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('scores_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_reports_symbol_created_at', 'ai_reports', ['symbol', sa.text('created_at DESC')])

    # ─────────────────────────────────────────────────────────────────────
    # 9. trade_signals
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'trade_signals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('underlying', sa.String(length=50), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('target_price', sa.Float(), nullable=True),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('bull_score', sa.Float(), nullable=True),
        sa.Column('bear_score', sa.Float(), nullable=True),
        sa.Column('risk_reward', sa.Float(), nullable=True),
        sa.Column('reasoning', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('factors', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('market_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trade_signals_symbol_created_at', 'trade_signals', ['symbol', sa.text('created_at DESC')])
    op.create_index('ix_trade_signals_status', 'trade_signals', ['status'])

    # ─────────────────────────────────────────────────────────────────────
    # 10. trade_journal — FK to trade_signals, nullable exit fields
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        'trade_journal',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('signal_id', sa.UUID(), nullable=True),
        sa.Column('symbol', sa.String(length=100), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_pct', sa.Float(), nullable=True),
        sa.Column('exit_reason', sa.Text(), nullable=True),
        sa.Column('entry_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        # Nullable — populated only on trade close
        sa.Column('exit_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('greeks_at_entry', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        # Nullable — populated only on trade close
        sa.Column('greeks_at_exit', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scores_at_entry', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('lessons', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ai_analysis', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['signal_id'], ['trade_signals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trade_journal_symbol_entry_time', 'trade_journal', ['symbol', sa.text('entry_time DESC')])
    op.create_index('ix_trade_journal_signal_id', 'trade_journal', ['signal_id'])


def downgrade() -> None:
    op.drop_table('trade_journal')
    op.drop_table('trade_signals')
    op.drop_table('ai_reports')
    op.drop_table('scoring_snapshots')
    op.drop_table('ml_predictions')
    op.drop_table('feature_store')
    op.drop_table('computed_metrics')
    op.drop_table('option_chain_snapshots')
    op.drop_table('market_ticks')
    op.drop_index(op.f('ix_instruments_underlying'), table_name='instruments')
    op.drop_index(op.f('ix_instruments_symbol'), table_name='instruments')
    op.drop_table('instruments')
