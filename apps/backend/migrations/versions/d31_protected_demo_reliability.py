"""protected demo provenance and outbox reliability

Revision ID: d31
Revises: c21outcomes
"""
from alembic import op
import sqlalchemy as sa

revision = "d31"
down_revision = "c21outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("outlet_id", sa.String(), nullable=True))
    op.add_column("events", sa.Column("scenario_run_id", sa.String(), nullable=True))
    op.execute("UPDATE events SET outlet_id = restaurant_id WHERE outlet_id IS NULL")
    op.alter_column("events", "outlet_id", nullable=False)
    op.create_index("ix_events_outlet_id", "events", ["outlet_id"])
    op.create_index("ix_events_scenario_run_id", "events", ["scenario_run_id"])
    op.add_column("events", sa.Column("outbox_claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("outbox_attempt_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("events", sa.Column("outbox_last_error", sa.String(), nullable=True))
    op.add_column("events", sa.Column("outbox_published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_events_outbox_claimed_at", "events", ["outbox_claimed_at"])


def downgrade() -> None:
    op.drop_index("ix_events_outbox_claimed_at", table_name="events")
    op.drop_column("events", "outbox_published_at")
    op.drop_column("events", "outbox_last_error")
    op.drop_column("events", "outbox_attempt_count")
    op.drop_column("events", "outbox_claimed_at")
    op.drop_index("ix_events_scenario_run_id", table_name="events")
    op.drop_index("ix_events_outlet_id", table_name="events")
    op.drop_column("events", "scenario_run_id")
    op.drop_column("events", "outlet_id")
