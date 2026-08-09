// LOSSLine API Types — derived from real backend schema

export type IncidentStatus =
  | 'DETECTED'
  | 'INVESTIGATING'
  | 'AWAITING_APPROVAL'
  | 'ACTION_APPROVED'
  | 'ACTION_REJECTED'
  | 'VERIFYING'
  | 'RESOLVED'
  | 'NOT_IMPROVED';

export interface Restaurant {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  synthetic: boolean;
  created_at: string;
  metadata_json: Record<string, unknown> | null;
}

export interface Signal {
  id: number;
  signal_type: string;
  severity: number;
  current_value: number;
  baseline_value: number | null;
  deviation: number | null;
  unit: string;
  window_start: string;
  window_end: string;
  evidence_event_ids: string[];
  detector_version: string;
  restaurant_id: string;
}

export interface ExpectedImpact {
  metric: string;
  direction: string;
  note: string;
}

export interface Recommendation {
  id: number;
  incident_id: number;
  rule_id: string;
  action_text: string;
  expected_impact: ExpectedImpact[];
  urgency: string;
  risk_tier: string;
  source: string;
  expires_at: string;
  created_at: string;
}

export interface Incident {
  id: number;
  restaurant_id: string;
  incident_type: string;
  status: IncidentStatus;
  severity: number;
  confidence: number;
  confidence_components: Record<string, unknown>;
  probable_cause: string | null;
  explanation: string | null;
  revenue_at_risk: number | null;
  currency: string;
  window_start: string;
  window_end: string;
  correlation_rule_version: string;
  config_version: string;
  created_at: string;
  updated_at: string;
  signals?: Signal[];
  recommendations?: Recommendation[];
}

export interface OutcomeMetric {
  metric: string;
  before: number;
  after: number;
  unit?: string;
}

export interface Outcome {
  id: number;
  incident_id: number;
  status: 'IMPROVED' | 'NO_CHANGE' | 'WORSENED' | 'INSUFFICIENT_DATA';
  baseline_metrics: Record<string, number>;
  post_metrics: Record<string, number>;
  check_after: string;
  evaluated_at: string | null;
  rule_version: string;
}

export interface AnalyticsSummary {
  incident_count: number;
  active_incident_count: number;
  resolved_incident_count: number;
  estimated_exposure: number;
  synthetic: boolean;
}

export interface DecisionPayload {
  decision: 'APPROVE' | 'REJECT' | 'EDIT';
  final_action_text?: string;
  manager_note?: string;
  idempotency_key: string;
}

export interface PredictiveForecast {
  forecast_id: string;
  outlet_id: string;
  sku_id: string;
  service_window: string;
  prediction_as_of: string;
  window_start: string;
  window_end: string;
  point_demand: string;
  lower_demand: string;
  upper_demand: string;
  model_version?: string;
  forecast_version?: string;
  interval_method: string;
  feature_snapshot_id: string;
  data_sufficient: boolean;
}

export interface PredictiveInventoryProjection {
  projection_id: string;
  forecast_id: string;
  sku_id: string;
  ending_inventory_point: number;
  shortage_point: number;
  surplus_point: number;
  stockout_risk: boolean;
  shortage_severity: string;
  stockout_window_fraction: string | null;
}

export interface PredictiveCapacityProjection {
  projection_id: string;
  forecast_id: string;
  utilization_point: string;
  utilization_lower: string;
  utilization_upper: string;
  risk_tier: string;
  overloaded: boolean;
  mean_preparation_minutes: string;
}

export interface PredictiveDriver {
  driver_id: string;
  forecast_id: string;
  feature_id: string;
  rank: number;
  direction: 'INCREASE' | 'DECREASE' | 'NEUTRAL';
  method: string;
  score: string;
  contribution: string | null;
  wording_limit: string;
}

export interface PredictiveDecisionView {
  decision: {
    decision_id: string;
    action: string;
    quantity: string | null;
    unit: string | null;
    approval_required: boolean;
  };
  status: string;
  manager_decision: string | null;
}

export interface PredictiveActualOutcome {
  outcome_id: string;
  forecast_id: string;
  actual_demand: string | null;
  fulfilled_quantity: string | null;
  unfulfilled_quantity: string | null;
  status: 'AVAILABLE' | 'CENSORED' | 'MISSING';
  matured_at: string;
}

export interface PredictiveToday {
  outlet_id: string;
  service_window: string;
  forecasts: PredictiveForecast[];
  inventory_projections: PredictiveInventoryProjection[];
  capacity_projections: PredictiveCapacityProjection[];
  risks: Array<Record<string, unknown>>;
  drivers: PredictiveDriver[];
  dossiers: Array<Record<string, unknown>>;
  decisions: PredictiveDecisionView[];
  outcomes: PredictiveActualOutcome[];
  synthetic: boolean;
}

export interface PredictiveAnalyticsSummary {
  forecast_count: number;
  risk_count: number;
  pending_review_count: number;
  synthetic: boolean;
}
