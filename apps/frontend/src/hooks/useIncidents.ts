import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { Incident, AnalyticsSummary } from '../types/api';

interface UseIncidentsResult {
  incidents: Incident[];
  summary: AnalyticsSummary | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useIncidents(): UseIncidentsResult {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const [incidentList, sum] = await Promise.all([
        api.getIncidents(),
        api.getSummary(),
      ]);
      if (!mountedRef.current) return;
      setIncidents(incidentList);
      setSummary(sum);
      setError(null);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err instanceof Error ? err.message : 'Unable to connect to LOSSLine.');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => {
      mountedRef.current = false;
      clearInterval(timer);
    };
  }, [refresh]);

  return { incidents, summary, loading, error, refresh };
}
