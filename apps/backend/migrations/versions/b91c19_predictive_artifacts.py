"""add predictive artifact persistence

Revision ID: b91c19predictive
Revises: a6cedb733e13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b91c19predictive"
down_revision: Union[str, None] = "a6cedb733e13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
J = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table("predictive_feature_snapshots",
        sa.Column("snapshot_id", sa.String(), primary_key=True),
        sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("sku_id", sa.String(), nullable=False), sa.Column("service_window", sa.String(), nullable=False),
        sa.Column("prediction_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False), sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registry_version", sa.String(), nullable=False), sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("payload", J, nullable=False))
    op.create_index("ix_predictive_feature_snapshots_outlet_id", "predictive_feature_snapshots", ["outlet_id"])
    op.create_table("forecast_results",
        sa.Column("forecast_id", sa.String(), primary_key=True), sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("sku_id", sa.String(), nullable=False), sa.Column("service_window", sa.String(), nullable=False),
        sa.Column("prediction_as_of", sa.DateTime(timezone=True), nullable=False), sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False), sa.Column("point_demand", sa.Numeric(18,4), nullable=False),
        sa.Column("lower_demand", sa.Numeric(18,4), nullable=False), sa.Column("upper_demand", sa.Numeric(18,4), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False), sa.Column("feature_snapshot_id", sa.String(), sa.ForeignKey("predictive_feature_snapshots.snapshot_id"), nullable=False),
        sa.Column("payload", J, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for column in ("outlet_id", "service_window", "window_start"): op.create_index(f"ix_forecast_results_{column}", "forecast_results", [column])
    op.create_table("inventory_projections", sa.Column("projection_id", sa.String(), primary_key=True),
        sa.Column("forecast_id", sa.String(), sa.ForeignKey("forecast_results.forecast_id"), nullable=False),
        sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False), sa.Column("sku_id", sa.String(), nullable=False),
        sa.Column("shortage_point", sa.Numeric(18,4), nullable=False), sa.Column("stockout_risk", sa.Boolean(), nullable=False), sa.Column("payload", J, nullable=False))
    op.create_index("ix_inventory_projections_forecast_id", "inventory_projections", ["forecast_id"]); op.create_index("ix_inventory_projections_outlet_id", "inventory_projections", ["outlet_id"])
    op.create_table("capacity_projections", sa.Column("projection_id", sa.String(), primary_key=True),
        sa.Column("forecast_id", sa.String(), nullable=False), sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("utilization_point", sa.Numeric(18,4), nullable=False), sa.Column("risk_tier", sa.String(), nullable=False),
        sa.Column("overloaded", sa.Boolean(), nullable=False), sa.Column("payload", J, nullable=False))
    op.create_index("ix_capacity_projections_forecast_id", "capacity_projections", ["forecast_id"]); op.create_index("ix_capacity_projections_outlet_id", "capacity_projections", ["outlet_id"])
    op.create_table("risk_candidates", sa.Column("risk_id", sa.String(), primary_key=True),
        sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False), sa.Column("forecast_id", sa.String(), nullable=False),
        sa.Column("risk_type", sa.String(), nullable=False), sa.Column("severity", sa.String(), nullable=False), sa.Column("payload", J, nullable=False))
    op.create_index("ix_risk_candidates_outlet_id", "risk_candidates", ["outlet_id"]); op.create_index("ix_risk_candidates_forecast_id", "risk_candidates", ["forecast_id"])
    op.create_table("driver_evidence", sa.Column("driver_id", sa.String(), primary_key=True), sa.Column("forecast_id", sa.String(), nullable=False),
        sa.Column("feature_id", sa.String(), nullable=False), sa.Column("rank", sa.Integer(), nullable=False), sa.Column("direction", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False), sa.Column("payload", J, nullable=False))
    op.create_index("ix_driver_evidence_forecast_id", "driver_evidence", ["forecast_id"])
    op.create_table("forecast_dossiers", sa.Column("dossier_id", sa.String(), primary_key=True),
        sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False), sa.Column("service_window", sa.String(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False), sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dossier_version", sa.String(), nullable=False), sa.Column("payload", J, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_forecast_dossiers_outlet_id", "forecast_dossiers", ["outlet_id"])
    op.create_table("predictive_decisions", sa.Column("decision_id", sa.String(), primary_key=True),
        sa.Column("dossier_id", sa.String(), sa.ForeignKey("forecast_dossiers.dossier_id"), nullable=False), sa.Column("outlet_id", sa.String(), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("action", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("payload", J, nullable=False), sa.Column("manager_decision", sa.String()), sa.Column("manager_id", sa.String()),
        sa.Column("manager_note", sa.String()), sa.Column("idempotency_key", sa.String(), unique=True), sa.Column("decided_at", sa.DateTime(timezone=True)))
    op.create_index("ix_predictive_decisions_dossier_id", "predictive_decisions", ["dossier_id"]); op.create_index("ix_predictive_decisions_outlet_id", "predictive_decisions", ["outlet_id"])
    op.create_table("guard_results", sa.Column("guard_result_id", sa.String(), primary_key=True),
        sa.Column("decision_id", sa.String(), sa.ForeignKey("predictive_decisions.decision_id"), nullable=False),
        sa.Column("disposition", sa.String(), nullable=False), sa.Column("valid", sa.Boolean(), nullable=False), sa.Column("payload", J, nullable=False))
    op.create_index("ix_guard_results_decision_id", "guard_results", ["decision_id"])
    op.create_table("decision_traces", sa.Column("trace_id", sa.String(), primary_key=True),
        sa.Column("dossier_id", sa.String(), sa.ForeignKey("forecast_dossiers.dossier_id"), nullable=False),
        sa.Column("decision_id", sa.String(), sa.ForeignKey("predictive_decisions.decision_id")),
        sa.Column("guard_result_id", sa.String(), sa.ForeignKey("guard_results.guard_result_id")), sa.Column("checkpoint_thread_id", sa.String()),
        sa.Column("payload", J, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_decision_traces_dossier_id", "decision_traces", ["dossier_id"])
    op.create_table("forecast_model_artifacts", sa.Column("artifact_id", sa.String(), primary_key=True),
        sa.Column("model_version", sa.String(), nullable=False), sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("training_cutoff", sa.DateTime(timezone=True), nullable=False), sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("payload", J, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    for table in ("forecast_model_artifacts", "decision_traces", "guard_results", "predictive_decisions", "forecast_dossiers",
                  "driver_evidence", "risk_candidates", "capacity_projections", "inventory_projections", "forecast_results", "predictive_feature_snapshots"):
        op.drop_table(table)
