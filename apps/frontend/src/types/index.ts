/**
 * TypeScript types mirroring lossline_intelligence/ Python models.
 * Outlet identity: outlet_id is canonical; restaurant_id is a legacy alias.
 */

// ── Enums (mirror Python StrEnums) ────────────────────────────────────────────

export type SignalType =
  | "ORDER_VOLUME_SPIKE"
  | "PREP_TIME_SPIKE"
  | "HANDOFF_DELAY_SPIKE"
  | "CANCELLATION_SPIKE"
  | "DELAY_REVIEW_SPIKE";

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ConfidenceTier = "INSUFFICIENT" | "LOW" | "MODERATE" | "HIGH";

export type IncidentType = "OPERATIONAL_OVERLOAD";

export type ServiceStatus =
  | "PREP"
  | "RUSH_HOUR"
  | "CLOSING"
  | "STAFF_MEETING"
  | "CLEAN_UP"
  | "ORDER_CUSTOMIZATION"
  | "ORDER_CONFIRMED"
  | "ACTIVE_COOKING"
  | "QUALITY_CONTROL_CHECK"
  | "ORDER_COMPLETE";

// ── Outlet ────────────────────────────────────────────────────────────────────

export interface Outlet {
  outlet_id: string;
  name: string;
  timezone: string;
  currency: "INR";
  /** Map position as fraction of card [0-1] */
  mapX: number;
  mapY: number;
}

// ── MetricSnapshot (mirrors aggregation/MetricSnapshot) ───────────────────────

export interface MetricSnapshot {
  outlet_id: string;
  window_start: string; // ISO UTC
  window_end: string;
  order_count: number;
  delivery_count: number;
  cancellation_count: number;
  cancellation_rate: number; // 0-1
  avg_prep_time_minutes: number;
  p90_prep_time_minutes: number;
  avg_handoff_wait_minutes: number;
  review_count: number;
  delay_review_count: number;
}

// ── Signal (mirrors models/Signal) ────────────────────────────────────────────

export interface Signal {
  signal_id: string;
  outlet_id: string;
  signal_type: SignalType;
  severity: Severity;
  deviation_ratio: number;
  window_start: string;
  detector_version: string;
}

// ── IncidentCandidate (mirrors models/IncidentCandidate) ─────────────────────

export interface IncidentCandidate {
  outlet_id: string;
  incident_type: IncidentType;
  severity: Severity;
  confidence_tier: ConfidenceTier;
  confidence_score: number; // 0-1
  revenue_risk_inr: number;
  recommendation_text: string;
  signal_ids: string[];
  window_start: string;
}

// ── Dashboard-level data shapes ───────────────────────────────────────────────

export interface DailyRevenue {
  day: string; // "Mon" … "Sun"
  value: number;
  isToday?: boolean;
}

export interface VenueCapacityDay {
  day: string;
  pct: number; // 0-100
}

export interface ServiceFlowPoint {
  date: number; // day of month
  ORDER_CUSTOMIZATION: number;
  ORDER_CONFIRMED: number;
  ACTIVE_COOKING: number;
  QUALITY_CONTROL_CHECK: number;
  ORDER_COMPLETE: number;
}

export interface ShiftRow {
  id: string;
  manager: string;
  location: string;
  date: string;
  status: ServiceStatus;
  hoursUntilClose: number;
  expectedRevenue: number;
}

export interface ChainMetric {
  label: "Week" | "Month" | "Quarter";
  achieved: number;
  total: number;
  description: string;
}

export interface AIMessage {
  role: "agent" | "user";
  text: string;
}
