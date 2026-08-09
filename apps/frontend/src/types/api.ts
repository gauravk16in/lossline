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
