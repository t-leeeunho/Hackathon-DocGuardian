import { useState, useCallback, useEffect } from 'react';
import type { MetricsDTO } from '../lib/types';
import { ApiError } from '../lib/api';
import { fixtureMetrics } from '../lib/fixtures';

/**
 * Live governance metrics (GET /metrics) with demo fallback.
 *
 * The typed API client (`lib/api.ts`) doesn't expose a `getMetrics` method, so
 * this hook performs a small fetch against the same `API_BASE`, surfacing the
 * same `ApiError` semantics (status 0 = backend unreachable) and falling back to
 * `fixtureMetrics` so the offline demo keeps working.
 */
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function fetchMetrics(): Promise<MetricsDTO> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/metrics`, {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    throw new ApiError(0, err instanceof Error ? err.message : 'Network error');
  }
  if (!res.ok) {
    throw new ApiError(res.status, res.statusText);
  }
  return (await res.json()) as MetricsDTO;
}

interface UseMetricsState {
  data: MetricsDTO;
  loading: boolean;
  /** True when we're showing fixture data because the API was unreachable. */
  offline: boolean;
}

export function useMetrics() {
  const [state, setState] = useState<UseMetricsState>({
    data: fixtureMetrics,
    loading: true,
    offline: false,
  });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    try {
      const data = await fetchMetrics();
      setState({ data, loading: false, offline: false });
    } catch {
      setState({ data: fixtureMetrics, loading: false, offline: true });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, refresh: load };
}
