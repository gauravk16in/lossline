import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { PredictiveToday } from '../types/api';

export function usePredictiveToday(outletId: string | null, serviceWindow: string) {
  const [data, setData] = useState<PredictiveToday | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!outletId) { setData(null); return; }
    setLoading(true); setError(null);
    try { setData(await api.getPredictiveToday(outletId, serviceWindow)); }
    catch (value) { setError(value instanceof Error ? value.message : 'Unable to load predictive data'); }
    finally { setLoading(false); }
  }, [outletId, serviceWindow]);

  useEffect(() => { void refresh(); }, [refresh]);
  return { data, loading, error, refresh };
}
