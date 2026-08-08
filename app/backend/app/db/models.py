import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    UniqueConstraint,
    Table,
    JSON
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
    Column("incident_id", Integer, ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column("signal_id", Integer, ForeignKey("signals.id", ondelete="CASCADE"), primary_key=True)
)

class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(String, primary_key=True, index=True)  # e.g., 'store_17'
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="UTC")
    currency = Column(String, nullable=False, default="INR")
    synthetic = Column(Boolean, nullable=False, default=True)
    metadata_json = Column("metadata", JSONB_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))

    events = relationship("Event", back_populates="restaurant")
    metric_windows = relationship("MetricWindow", back_populates="restaurant")
    signals = relationship("Signal", back_populates="restaurant")
    incidents = relationship("Incident", back_populates="restaurant")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    source = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    entity = Column(JSONB_TYPE, nullable=False)
    data = Column(JSONB_TYPE, nullable=False)
    metadata_json = Column("metadata", JSONB_TYPE, nullable=False)
    schema_version = Column(String, nullable=False)
    payload_hash = Column(String, nullable=False)
    published_to_stream = Column(Boolean, default=False, nullable=False, index=True)

    restaurant = relationship("Restaurant", back_populates="events")

class MetricWindow(Base):
    __tablename__ = "metric_windows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    baseline_value = Column(Float, nullable=True)
    dispersion = Column(Float, nullable=True)
    config_version = Column(String, nullable=False)

    restaurant = relationship("Restaurant", back_populates="metric_windows")

    __table_args__ = (
        UniqueConstraint("restaurant_id", "window_start", "window_end", "metric_name", name="uq_metric_window"),
    )

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    signal_type = Column(String, nullable=False)
    severity = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=True)
    deviation = Column(Float, nullable=True)
    unit = Column(String, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    evidence_event_ids = Column(JSONB_TYPE, nullable=False)  # List of event_id strings
    detector_version = Column(String, nullable=False)

    restaurant = relationship("Restaurant", back_populates="signals")
    incidents = relationship("Incident", secondary=incident_signals, back_populates="signals")

    __table_args__ = (
        UniqueConstraint("restaurant_id", "signal_type", "window_start", "window_end", name="uq_signal"),
    )

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id"), nullable=False)
    incident_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="DETECTED")  # DETECTED, INVESTIGATING, AWAITING_APPROVAL, etc.
    severity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    confidence_components = Column(JSONB_TYPE, nullable=False)
    probable_cause = Column(String, nullable=True)
    explanation = Column(String, nullable=True)
    revenue_at_risk = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="INR")
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    correlation_rule_version = Column(String, nullable=False)
    config_version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    restaurant = relationship("Restaurant", back_populates="incidents")
    signals = relationship("Signal", secondary=incident_signals, back_populates="incidents")
    recommendations = relationship("Recommendation", back_populates="incident", cascade="all, delete-orphan")
    outcome = relationship("Outcome", uselist=False, back_populates="incident", cascade="all, delete-orphan")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(String, nullable=False)
    action_text = Column(String, nullable=False)
    expected_impact = Column(JSONB_TYPE, nullable=False)
    urgency = Column(String, nullable=False)
    risk_tier = Column(String, nullable=False)
    source = Column(String, nullable=False)  # RULE or LLM_FALLBACK
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))

    incident = relationship("Incident", back_populates="recommendations")
    actions = relationship("Action", back_populates="recommendation", cascade="all, delete-orphan")

class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    decision = Column(String, nullable=False)  # APPROVE, REJECT, EDIT
    suggested_text = Column(String, nullable=False)
    final_text = Column(String, nullable=False)
    decided_by = Column(String, nullable=False)  # Manager identifier (A8)
    decided_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    execution_status = Column(String, nullable=False, default="PENDING")  # PENDING, EXECUTED, EXECUTION_FAILED
    executed_at = Column(DateTime(timezone=True), nullable=True)
    manager_note = Column(String, nullable=True)
    idempotency_key = Column(String, unique=True, nullable=False)

    recommendation = relationship("Recommendation", back_populates="actions")

class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String, nullable=False)  # IMPROVED, NO_CHANGE, WORSENED, INSUFFICIENT_DATA
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
    status = Column(String, nullable=False, default="RUNNING")  # RUNNING, COMPLETED, FAILED
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
