import type {
  Incident,
  Restaurant,
  AnalyticsSummary,
  Outcome,
  DecisionPayload,
} from '../types/api';

const BASE: string = import.meta.env.VITE_API_URL ?? '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getRestaurants: () => request<Restaurant[]>('/api/v1/restaurants'),

  getIncidents: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return request<Incident[]>(`/api/v1/incidents${qs}`);
  },

  getIncident: (id: number) => request<Incident>(`/api/v1/incidents/${id}`),

  getOutcome: (id: number) => request<Outcome>(`/api/v1/incidents/${id}/outcome`),

  getSummary: () => request<AnalyticsSummary>('/api/v1/analytics/summary'),

  submitDecision: (id: number, payload: DecisionPayload) =>
    request<{ status: string; action_id: number; duplicate: boolean }>(
      `/api/v1/incidents/${id}/decision`,
      { method: 'POST', body: JSON.stringify(payload) }
    ),

  verifyOutcome: (id: number) => request<Outcome>(`/api/v1/incidents/${id}/verify`, { method: 'POST' }),

  resetDemo: () => request<{ status: string; detail: string }>('/api/v1/demo/reset', { method: 'POST' }),
};
