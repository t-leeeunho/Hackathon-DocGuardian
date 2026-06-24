import { useState, useCallback, useEffect } from 'react';
import type { GraphDTO } from '../lib/types';
import { api } from '../lib/api';
import { fixtureGraph } from '../lib/fixtures';

interface UseGraphState {
  data: GraphDTO;
  loading: boolean;
  error: string | null;
  offline: boolean;
}

export function useGraph(repo?: string) {
  const [state, setState] = useState<UseGraphState>({
    data: { nodes: [], edges: [] },
    loading: true,
    error: null,
    offline: false,
  });

  const load = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const data = await api.getGraph(repo);
      setState({ data, loading: false, error: null, offline: false });
    } catch {
      // Fall back to fixtures when backend is unavailable
      setState({
        data: fixtureGraph,
        loading: false,
        error: null,
        offline: true,
      });
    }
  }, [repo]);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, refresh: load };
}
