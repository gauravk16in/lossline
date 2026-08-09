"""add matured predictive outcomes and evaluations

Revision ID: c21outcomes
Revises: b91c19predictive
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c21outcomes"
down_revision: Union[str, None] = "b91c19predictive"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
J = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table("actual_outcomes",
        sa.Column("outcome_id", sa.String(), primary_key=True),
        sa.Column("forecast_id", sa.String(), sa.ForeignKey("forecast_results.forecast_id"), nullable=False, unique=True),
        sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("sku_id", sa.String(), nullable=False), sa.Column("service_window", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False), sa.Column("matured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", J, nullable=False))
    op.create_index("ix_actual_outcomes_forecast_id", "actual_outcomes", ["forecast_id"])
    op.create_index("ix_actual_outcomes_outlet_id", "actual_outcomes", ["outlet_id"])
    op.create_table("predictive_evaluations",
        sa.Column("evaluation_id", sa.String(), primary_key=True), sa.Column("evaluation_type", sa.String(), nullable=False),
        sa.Column("forecast_id", sa.String(), sa.ForeignKey("forecast_results.forecast_id"), nullable=False),
        sa.Column("outcome_id", sa.String(), sa.ForeignKey("actual_outcomes.outcome_id"), nullable=False),
        sa.Column("decision_id", sa.String(), sa.ForeignKey("predictive_decisions.decision_id")),
        sa.Column("payload", J, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_predictive_evaluations_forecast_id", "predictive_evaluations", ["forecast_id"])
    op.create_index("ix_predictive_evaluations_outcome_id", "predictive_evaluations", ["outcome_id"])


def downgrade() -> None:
    op.drop_table("predictive_evaluations")
    op.drop_table("actual_outcomes")
