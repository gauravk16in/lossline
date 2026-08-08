/**
 * Mock data layer — mirrors lossline_intelligence/ Python contracts.
 * All values are SYNTHETIC DATA FOR DEMONSTRATION.
 * Swap fetch() calls here once the FastAPI backend is running.
 */

import type {
  Outlet,
  DailyRevenue,
  VenueCapacityDay,
  ServiceFlowPoint,
  ShiftRow,
  ChainMetric,
  IncidentCandidate,
  AIMessage,
} from "@/types";

// ── Outlets ────────────────────────────────────────────────────────────────────

export const OUTLETS: Outlet[] = [
  { outlet_id: "KOR001", name: "Koramangala", timezone: "Asia/Kolkata", currency: "INR", mapX: 0.42, mapY: 0.52 },
  { outlet_id: "IND002", name: "Indiranagar",  timezone: "Asia/Kolkata", currency: "INR", mapX: 0.68, mapY: 0.28 },
  { outlet_id: "JAY003", name: "Jayanagar",    timezone: "Asia/Kolkata", currency: "INR", mapX: 0.30, mapY: 0.72 },
  { outlet_id: "MAR004", name: "Marathahalli", timezone: "Asia/Kolkata", currency: "INR", mapX: 0.74, mapY: 0.60 },
];

// ── Revenue (per outlet) ───────────────────────────────────────────────────────

export const REVENUE_BY_OUTLET: Record<string, DailyRevenue[]> = {
  KOR001: [
    { day: "Mon", value: 21000 },
    { day: "Tue", value: 18500 },
    { day: "Wed", value: 24800, isToday: true },
    { day: "Thu", value: 22000 },
    { day: "Fri", value: 27000 },
    { day: "Sat", value: 31000 },
    { day: "Sun", value: 28500 },
  ],
  IND002: [
    { day: "Mon", value: 17200 },
    { day: "Tue", value: 19800 },
    { day: "Wed", value: 21150, isToday: true },
    { day: "Thu", value: 20000 },
    { day: "Fri", value: 24000 },
    { day: "Sat", value: 26500 },
    { day: "Sun", value: 23000 },
  ],
  JAY003: [
    { day: "Mon", value: 14000 },
    { day: "Tue", value: 15500 },
    { day: "Wed", value: 16900, isToday: true },
    { day: "Thu", value: 15200 },
    { day: "Fri", value: 18000 },
    { day: "Sat", value: 21000 },
    { day: "Sun", value: 19500 },
  ],
  MAR004: [
    { day: "Mon", value: 19000 },
    { day: "Tue", value: 20500 },
    { day: "Wed", value: 23200, isToday: true },
    { day: "Thu", value: 21000 },
    { day: "Fri", value: 25000 },
    { day: "Sat", value: 28000 },
    { day: "Sun", value: 26000 },
  ],
};

export const GROSS_REVENUE_BY_OUTLET: Record<string, number> = {
  KOR001: 156900,
  IND002: 131050,
  JAY003: 100100,
  MAR004: 142700,
};

export const AOV_BY_OUTLET: Record<string, number> = {
  KOR001: 485,
  IND002: 420,
  JAY003: 360,
  MAR004: 455,
};

// ── Venue Capacity (per outlet) ────────────────────────────────────────────────

export const CAPACITY_BY_OUTLET: Record<string, VenueCapacityDay[]> = {
  KOR001: [
    { day: "Mon", pct: 78 }, { day: "Tue", pct: 82 }, { day: "Wed", pct: 91 },
    { day: "Thu", pct: 88 }, { day: "Fri", pct: 95 }, { day: "Sat", pct: 93 }, { day: "Sun", pct: 76 },
  ],
  IND002: [
    { day: "Mon", pct: 65 }, { day: "Tue", pct: 70 }, { day: "Wed", pct: 80 },
    { day: "Thu", pct: 75 }, { day: "Fri", pct: 88 }, { day: "Sat", pct: 90 }, { day: "Sun", pct: 72 },
  ],
  JAY003: [
    { day: "Mon", pct: 55 }, { day: "Tue", pct: 60 }, { day: "Wed", pct: 68 },
    { day: "Thu", pct: 62 }, { day: "Fri", pct: 74 }, { day: "Sat", pct: 80 }, { day: "Sun", pct: 66 },
  ],
  MAR004: [
    { day: "Mon", pct: 72 }, { day: "Tue", pct: 77 }, { day: "Wed", pct: 85 },
    { day: "Thu", pct: 82 }, { day: "Fri", pct: 92 }, { day: "Sat", pct: 95 }, { day: "Sun", pct: 78 },
  ],
};

// ── Operational Timing (per outlet) ───────────────────────────────────────────

export const TIMING_BY_OUTLET: Record<string, { prepMins: number; handoffMins: number; targetPrepMins: number; targetHandoffMins: number }> = {
  KOR001: { prepMins: 18.4, handoffMins: 6.2, targetPrepMins: 15, targetHandoffMins: 5 },
  IND002: { prepMins: 14.8, handoffMins: 4.9, targetPrepMins: 15, targetHandoffMins: 5 },
  JAY003: { prepMins: 22.1, handoffMins: 8.5, targetPrepMins: 15, targetHandoffMins: 5 },
  MAR004: { prepMins: 16.3, handoffMins: 5.8, targetPrepMins: 15, targetHandoffMins: 5 },
};

// ── Incident (per outlet) ──────────────────────────────────────────────────────

export const INCIDENT_BY_OUTLET: Record<string, IncidentCandidate | null> = {
  KOR001: {
    outlet_id: "KOR001",
    incident_type: "OPERATIONAL_OVERLOAD",
    severity: "HIGH",
    confidence_tier: "HIGH",
    confidence_score: 0.87,
    revenue_risk_inr: 24800,
    recommendation_text: "Activate surge staffing protocol — two additional KDS operators recommended for the next 45 minutes.",
    signal_ids: ["sig_prep_KOR001_2024W02_v1", "sig_cancel_KOR001_2024W02_v1"],
    window_start: "2024-01-09T12:00:00Z",
  },
  IND002: null,
  JAY003: {
    outlet_id: "JAY003",
    incident_type: "OPERATIONAL_OVERLOAD",
    severity: "MEDIUM",
    confidence_tier: "MODERATE",
    confidence_score: 0.64,
    revenue_risk_inr: 12400,
    recommendation_text: "Monitor prep queue — consider pre-staging high-frequency menu items.",
    signal_ids: ["sig_prep_JAY003_2024W02_v1"],
    window_start: "2024-01-09T12:15:00Z",
  },
  MAR004: null,
};

// ── AI Messages (per outlet) ───────────────────────────────────────────────────

export const AI_MESSAGES_BY_OUTLET: Record<string, AIMessage[]> = {
  KOR001: [
    { role: "agent", text: "Koramangala shows strong revenue, but two flags need attention: prep time is elevated (+23%) and cancellation spike detected. Revenue risk: ₹24,800. Recommend surge staffing." },
  ],
  IND002: [
    { role: "agent", text: "Indiranagar is operating within normal parameters. All five detectors below threshold. Capacity at 80% — looking healthy for the evening rush." },
  ],
  JAY003: [
    { role: "agent", text: "Jayanagar has a moderate overload signal. Prep time deviation ratio is +47%. Monitor closely — if cancellations rise, escalate to CRITICAL." },
  ],
  MAR004: [
    { role: "agent", text: "Marathahalli metrics are nominal. AOV trending up +3.2% vs. last week baseline. No active incident candidates." },
  ],
};

// ── Activity Page Data ─────────────────────────────────────────────────────────

export const SERVICE_FLOW_DATA: ServiceFlowPoint[] = Array.from({ length: 30 }, (_, i) => {
  const base = 200 + Math.round(Math.sin(i / 5) * 60 + i * 4);
  return {
    date: i + 1,
    ORDER_CUSTOMIZATION: Math.round(base * 0.18),
    ORDER_CONFIRMED:     Math.round(base * 0.22),
    ACTIVE_COOKING:      Math.round(base * 0.28),
    QUALITY_CONTROL_CHECK: Math.round(base * 0.16),
    ORDER_COMPLETE:      Math.round(base * 0.16),
  };
});

export const SHIFTS_DATA: ShiftRow[] = [
  { id: "s1",  manager: "Priya Sharma",     location: "Koramangala",  date: "Today",    status: "RUSH_HOUR",           hoursUntilClose: 6.5, expectedRevenue: 32000 },
  { id: "s2",  manager: "Arun Mehta",       location: "Indiranagar",  date: "Today",    status: "STAFF_MEETING",       hoursUntilClose: 5.0, expectedRevenue: 28000 },
  { id: "s3",  manager: "Kavitha Nair",     location: "Jayanagar",    date: "Today",    status: "RUSH_HOUR",           hoursUntilClose: 4.5, expectedRevenue: 19500 },
  { id: "s4",  manager: "Rohit Gupta",      location: "Marathahalli", date: "Today",    status: "RUSH_HOUR",           hoursUntilClose: 5.5, expectedRevenue: 29000 },
  { id: "s5",  manager: "Deepa Iyer",       location: "Koramangala",  date: "Jan 8",    status: "CLOSING",             hoursUntilClose: 4.0, expectedRevenue: 16000 },
  { id: "s6",  manager: "Suresh Rao",       location: "Indiranagar",  date: "Jan 8",    status: "CLOSING",             hoursUntilClose: 3.5, expectedRevenue: 21000 },
  { id: "s7",  manager: "Meena Pillai",     location: "Jayanagar",    date: "Jan 8",    status: "CLOSING",             hoursUntilClose: 3.0, expectedRevenue: 14500 },
  { id: "s8",  manager: "Vikram Joshi",     location: "Marathahalli", date: "Jan 8",    status: "CLOSING",             hoursUntilClose: 2.5, expectedRevenue: 9800 },
  { id: "s9",  manager: "Anitha Reddy",     location: "Koramangala",  date: "Jan 7",    status: "CLEAN_UP",            hoursUntilClose: 2.0, expectedRevenue: 35000 },
  { id: "s10", manager: "Ganesh Kumar",     location: "Marathahalli", date: "Jan 7",    status: "STAFF_MEETING",       hoursUntilClose: 1.0, expectedRevenue: 42000 },
];

export const CHAIN_METRICS: ChainMetric[] = [
  { label: "Week",    achieved: 15,  total: 27,  description: "15 of 27 locations hit their daily targets" },
  { label: "Month",   achieved: 25,  total: 45,  description: "25 of 45 location-days met expectations" },
  { label: "Quarter", achieved: 65,  total: 120, description: "65 of 120 high-performance days achieved" },
];
