import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Table,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship

# Helper to support JSONB in Postgres and standard JSON fallback in SQLite for testing
JSONB_TYPE = JSONB().with_variant(JSON, "sqlite")


class Base(DeclarativeBase):
    pass


# Association table for Incident and Signal (many-to-many)
incident_signals = Table(
    "incident_signals",
    Base.metadata,
    Column(
        "incident_id",
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "signal_id",
        Integer,
        ForeignKey("signals.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(String, primary_key=True, index=True)  # e.g., 'meghana_indiranagar'
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="UTC")
    currency = Column(String, nullable=False, default="INR")
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    synthetic = Column(Boolean, nullable=False, default=False)
    metadata_json = Column("metadata", JSONB_TYPE, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    events = relationship("Event", back_populates="restaurant")
    metric_windows = relationship("MetricWindow", back_populates="restaurant")
    signals = relationship("Signal", back_populates="restaurant")
    incidents = relationship("Incident", back_populates="restaurant")


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    clerk_organization_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)


class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    public_prefix = Column(String, unique=True, nullable=False, index=True)
    secret_hash = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    allowed_outlet_ids = Column(JSONB_TYPE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    bucket_key = Column(String, primary_key=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    request_count = Column(Integer, nullable=False, default=0)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    outlet_id = Column(
        String,
        nullable=False,
        index=True,
        default=lambda context: context.get_current_parameters()["restaurant_id"],
    )
    scenario_run_id = Column(String, nullable=True, index=True)
    source = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    entity = Column(JSONB_TYPE, nullable=False)
    data = Column(JSONB_TYPE, nullable=False)
    metadata_json = Column("metadata", JSONB_TYPE, nullable=False)
    schema_version = Column(String, nullable=False)
    payload_hash = Column(String, nullable=False)
    published_to_stream = Column(Boolean, default=False, nullable=False, index=True)
    outbox_claimed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    outbox_attempt_count = Column(Integer, nullable=False, default=0)
    outbox_last_error = Column(String, nullable=True)
    outbox_published_at = Column(DateTime(timezone=True), nullable=True)
    processing_status = Column(String, nullable=False, default="PENDING", index=True)
    processing_attempt_count = Column(Integer, nullable=False, default=0)
    processing_last_error = Column(String, nullable=True)
    processing_result = Column(JSONB_TYPE, nullable=True)

    restaurant = relationship("Restaurant", back_populates="events")


class MetricWindow(Base):
    __tablename__ = "metric_windows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    metric_name = Column(String, nullable=False)
    value = Column(Numeric(18, 4), nullable=False)
    sample_count = Column(Integer, nullable=False)
    baseline_value = Column(Numeric(18, 4), nullable=True)
    dispersion = Column(Numeric(18, 4), nullable=True)
    config_version = Column(String, nullable=False)

    restaurant = relationship("Restaurant", back_populates="metric_windows")

    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            "window_start",
            "window_end",
            "metric_name",
            name="uq_metric_window",
        ),
    )


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    signal_type = Column(String, nullable=False)
    severity = Column(Float, nullable=False)
    current_value = Column(Numeric(18, 4), nullable=False)
    baseline_value = Column(Numeric(18, 4), nullable=True)
    deviation = Column(Numeric(18, 4), nullable=True)
    unit = Column(String, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    evidence_event_ids = Column(JSONB_TYPE, nullable=False)  # List of event_id strings
    detector_version = Column(String, nullable=False)

    restaurant = relationship("Restaurant", back_populates="signals")
    incidents = relationship(
        "Incident", secondary=incident_signals, back_populates="signals"
    )

    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            "signal_type",
            "window_start",
            "window_end",
            name="uq_signal",
        ),
    )


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    incident_type = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="DETECTED"
    )  # DETECTED, INVESTIGATING, AWAITING_APPROVAL, etc.
    severity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    confidence_components = Column(JSONB_TYPE, nullable=False)
    probable_cause = Column(String, nullable=True)
    explanation = Column(String, nullable=True)
    revenue_at_risk = Column(Numeric(18, 4), nullable=True)
    currency = Column(String, nullable=False, default="INR")
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    correlation_rule_version = Column(String, nullable=False)
    config_version = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    restaurant = relationship("Restaurant", back_populates="incidents")
    signals = relationship(
        "Signal", secondary=incident_signals, back_populates="incidents"
    )
    recommendations = relationship(
        "Recommendation", back_populates="incident", cascade="all, delete-orphan"
    )
    outcome = relationship(
        "Outcome",
        uselist=False,
        back_populates="incident",
        cascade="all, delete-orphan",
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    rule_id = Column(String, nullable=False)
    action_text = Column(String, nullable=False)
    expected_impact = Column(JSONB_TYPE, nullable=False)
    urgency = Column(String, nullable=False)
    risk_tier = Column(String, nullable=False)
    source = Column(String, nullable=False)  # RULE or LLM_FALLBACK
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    incident = relationship("Incident", back_populates="recommendations")
    actions = relationship(
        "Action", back_populates="recommendation", cascade="all, delete-orphan"
    )


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
    )
    decision = Column(String, nullable=False)  # APPROVE, REJECT, EDIT
    suggested_text = Column(String, nullable=False)
    final_text = Column(String, nullable=False)
    decided_by = Column(String, nullable=False)  # Manager identifier (A8)
    decided_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    execution_status = Column(
        String, nullable=False, default="PENDING"
    )  # PENDING, EXECUTED, EXECUTION_FAILED
    executed_at = Column(DateTime(timezone=True), nullable=True)
    manager_note = Column(String, nullable=True)
    idempotency_key = Column(String, unique=True, nullable=False)

    recommendation = relationship("Recommendation", back_populates="actions")


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status = Column(
        String, nullable=False
    )  # IMPROVED, NO_CHANGE, WORSENED, INSUFFICIENT_DATA
    baseline_metrics = Column(JSONB_TYPE, nullable=False)
    post_metrics = Column(JSONB_TYPE, nullable=False)
    check_after = Column(DateTime(timezone=True), nullable=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    rule_version = Column(String, nullable=False)

    incident = relationship("Incident", back_populates="outcome")


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(String, nullable=False)
    seed = Column(Integer, nullable=False)
    speed = Column(Float, nullable=False)
    status = Column(
        String, nullable=False, default="RUNNING"
    )  # RUNNING, COMPLETED, FAILED
    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


# Predictive artifacts are additive during reactive/predictive coexistence.
# Each row stores queryable identity/scope plus the complete validated contract payload.
class PredictiveFeatureSnapshot(Base):
    __tablename__ = "predictive_feature_snapshots"
    snapshot_id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    sku_id = Column(String, nullable=False)
    service_window = Column(String, nullable=False)
    prediction_as_of = Column(DateTime(timezone=True), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    registry_version = Column(String, nullable=False)
    fingerprint = Column(String, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)


class ForecastRecord(Base):
    __tablename__ = "forecast_results"
    forecast_id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    sku_id = Column(String, nullable=False)
    service_window = Column(String, nullable=False, index=True)
    prediction_as_of = Column(DateTime(timezone=True), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    window_end = Column(DateTime(timezone=True), nullable=False)
    point_demand = Column(Numeric(18, 4), nullable=False)
    lower_demand = Column(Numeric(18, 4), nullable=False)
    upper_demand = Column(Numeric(18, 4), nullable=False)
    model_version = Column(String, nullable=False)
    feature_snapshot_id = Column(String, ForeignKey("predictive_feature_snapshots.snapshot_id"), nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)


class InventoryProjectionRecord(Base):
    __tablename__ = "inventory_projections"
    projection_id = Column(String, primary_key=True)
    forecast_id = Column(String, ForeignKey("forecast_results.forecast_id"), nullable=False, index=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    sku_id = Column(String, nullable=False)
    shortage_point = Column(Numeric(18, 4), nullable=False)
    stockout_risk = Column(Boolean, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)


class CapacityProjectionRecord(Base):
    __tablename__ = "capacity_projections"
    projection_id = Column(String, primary_key=True)
    forecast_id = Column(String, nullable=False, index=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    utilization_point = Column(Numeric(18, 4), nullable=False)
    risk_tier = Column(String, nullable=False)
    overloaded = Column(Boolean, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)


class RiskCandidateRecord(Base):
    __tablename__ = "risk_candidates"
    risk_id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    forecast_id = Column(String, nullable=False, index=True)
    risk_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)


class DriverEvidenceRecord(Base):
    __tablename__ = "driver_evidence"
    driver_id = Column(String, primary_key=True)
    forecast_id = Column(String, nullable=False, index=True)
    feature_id = Column(String, nullable=False)
    rank = Column(Integer, nullable=False)
    direction = Column(String, nullable=False)
    method = Column(String, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)


class ForecastDossierRecord(Base):
    __tablename__ = "forecast_dossiers"
    dossier_id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    service_window = Column(String, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    dossier_version = Column(String, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)


class PredictiveDecisionRecord(Base):
    __tablename__ = "predictive_decisions"
    decision_id = Column(String, primary_key=True)
    dossier_id = Column(String, ForeignKey("forecast_dossiers.dossier_id"), nullable=False, index=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False, default="AWAITING_MANAGER_REVIEW")
    approval_required = Column(Boolean, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)
    manager_decision = Column(String, nullable=True)
    manager_id = Column(String, nullable=True)
    manager_note = Column(String, nullable=True)
    idempotency_key = Column(String, unique=True, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)


class GuardResultRecord(Base):
    __tablename__ = "guard_results"
    guard_result_id = Column(String, primary_key=True)
    decision_id = Column(String, ForeignKey("predictive_decisions.decision_id"), nullable=False, index=True)
    disposition = Column(String, nullable=False)
    valid = Column(Boolean, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)


class DecisionTraceRecord(Base):
    __tablename__ = "decision_traces"
    trace_id = Column(String, primary_key=True)
    dossier_id = Column(String, ForeignKey("forecast_dossiers.dossier_id"), nullable=False, index=True)
    decision_id = Column(String, ForeignKey("predictive_decisions.decision_id"), nullable=True)
    guard_result_id = Column(String, ForeignKey("guard_results.guard_result_id"), nullable=True)
    checkpoint_thread_id = Column(String, nullable=True)
    payload = Column(JSONB_TYPE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)


class ForecastModelArtifactRecord(Base):
    __tablename__ = "forecast_model_artifacts"
    artifact_id = Column(String, primary_key=True)
    model_version = Column(String, nullable=False)
    accepted = Column(Boolean, nullable=False)
    training_cutoff = Column(DateTime(timezone=True), nullable=False)
    checksum = Column(String, nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)


class ActualOutcomeRecord(Base):
    __tablename__ = "actual_outcomes"
    outcome_id = Column(String, primary_key=True)
    forecast_id = Column(String, ForeignKey("forecast_results.forecast_id"), nullable=False, unique=True, index=True)
    outlet_id = Column(String, ForeignKey("restaurants.id"), nullable=False, index=True)
    sku_id = Column(String, nullable=False)
    service_window = Column(String, nullable=False)
    status = Column(String, nullable=False)
    matured_at = Column(DateTime(timezone=True), nullable=False)
    payload = Column(JSONB_TYPE, nullable=False)


class PredictiveEvaluationRecord(Base):
    __tablename__ = "predictive_evaluations"
    evaluation_id = Column(String, primary_key=True)
    evaluation_type = Column(String, nullable=False)
    forecast_id = Column(String, ForeignKey("forecast_results.forecast_id"), nullable=False, index=True)
    outcome_id = Column(String, ForeignKey("actual_outcomes.outcome_id"), nullable=False, index=True)
    decision_id = Column(String, ForeignKey("predictive_decisions.decision_id"), nullable=True)
    payload = Column(JSONB_TYPE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
