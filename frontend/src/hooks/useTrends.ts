import { useState, useCallback, useEffect } from 'react';
import type { TrendsDTO } from '../lib/types';
import { api } from '../lib/api';
import { fixtureTrends } from '../lib/fixtures';

interface UseTrendsState {
  data: TrendsDTO;
  loading: boolean;
  error: string | null;
  /** True when we're showing fixture data because the API was unreachable. */
  offline: boolean;
}

/**
 * Corpus governance/insights trends (GET /analysis/trends) with demo fallback.
 * Same offline-first contract as `useGraph` / `useAnalysis`.
 */
export function useTrends(repo?: string) {
  const [state, setState] = useState<UseTrendsState>({
    data: fixtureTrends,
    loading: true,
    error: null,
    offline: false,
  });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await api.getTrends(repo);
      setState({ data, loading: false, error: null, offline: false });
    } catch {
      setState({ data: fixtureTrends, loading: false, error: null, offline: true });
    }
  }, [repo]);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, refresh: load };
}
