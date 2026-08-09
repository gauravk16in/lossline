import type { AnalyticsSummary, Incident, PredictiveToday, Restaurant } from '../types/api';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(problem?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  restaurants: () => request<Restaurant[]>('/restaurants'),
  predictiveToday: (outletId: string, serviceWindow: string) => request<PredictiveToday>(`/predictive/today/${encodeURIComponent(outletId)}/${encodeURIComponent(serviceWindow)}`),
  predictiveSummary: () => request<{ forecast_count: number; risk_count: number; pending_review_count: number; synthetic: boolean }>('/predictive/analytics/summary'),
  incidents: () => request<Incident[]>('/incidents'),
  analytics: () => request<AnalyticsSummary>('/analytics/summary'),
  reviewDecision: (decisionId: string, decision: 'APPROVE' | 'REJECT', note?: string) => request<{ decision_id: string; status: string; duplicate: boolean }>(`/predictive/decisions/${encodeURIComponent(decisionId)}/review`, {
    method: 'POST',
    body: JSON.stringify({ decision, manager_id: 'dashboard_manager', manager_note: note || null, idempotency_key: `dashboard-${decisionId}-${decision.toLowerCase()}` }),
  }),
};
