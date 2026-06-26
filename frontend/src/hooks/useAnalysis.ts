import { useState, useCallback, useEffect } from 'react';
import type { AnalysisReport, DocAnalysis, GraphNode } from '../lib/types';
import { api } from '../lib/api';
import {
  fixtureAnalysisReport,
  fixtureDocAnalysis,
  synthesizeDocAnalysis,
} from '../lib/fixtures';

/**
 * Insights data hooks. They mirror the offline-first fallback pattern of
 * `useGraph`: call the typed API client, and on any failure (the client throws
 * `ApiError` — status 0 when the backend is unreachable) fall back to the demo
 * fixture so the UI keeps working without a backend. Each exposes
 * `data` / `loading` / `error` / `offline` plus a refetch.
 */

interface UseAnalysisState {
  data: AnalysisReport;
  loading: boolean;
  error: string | null;
  /** True when we're showing fixture data because the API was unreachable. */
  offline: boolean;
}

/** Corpus-wide analysis report (GET /analysis) with demo fallback. */
export function useAnalysis(repo?: string) {
  const [state, setState] = useState<UseAnalysisState>({
    data: fixtureAnalysisReport,
    loading: true,
    error: null,
    offline: false,
  });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await api.getAnalysis(repo);
      setState({ data, loading: false, error: null, offline: false });
    } catch {
      // Backend unavailable -> demo fixtures (offline/demo mode).
      setState({ data: fixtureAnalysisReport, loading: false, error: null, offline: true });
    }
  }, [repo]);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, refresh: load };
}

interface UseDocAnalysisState {
  data: DocAnalysis | null;
  loading: boolean;
  error: string | null;
  offline: boolean;
  /** True while the opt-in LLM notes are being fetched. */
  llmLoading: boolean;
  /** True once the user has asked for LLM notes (drives the empty/disabled state). */
  llmRequested: boolean;
}

/**
 * Per-doc analysis (GET /analysis/{docId}) with demo fallback. `explainWithAi`
 * re-fetches with `?llm=true` to populate the opt-in `LlmQualityNotes`; when the
 * backend is offline (or returns `llm: null`) it degrades gracefully.
 */
export function useDocAnalysis(docId: string | null, node?: GraphNode | null) {
  const [state, setState] = useState<UseDocAnalysisState>({
    data: null,
    loading: false,
    error: null,
    offline: false,
    llmLoading: false,
    llmRequested: false,
  });

  // Stable scalar signature of the node overlay so passing the object as a
  // dependency can't trigger a re-fetch loop, while still re-running if the
  // overlay fields actually change (e.g. the graph finishes loading).
  const nodeKey = node
    ? `${node.id}:${node.health}:${node.qualityScore ?? ''}:${node.brokenLinkCount ?? ''}:${node.orphan ?? ''}:${node.centrality ?? ''}`
    : '';

  const load = useCallback(async () => {
    if (!docId) {
      setState({
        data: null,
        loading: false,
        error: null,
        offline: false,
        llmLoading: false,
        llmRequested: false,
      });
      return;
    }
    setState((s) => ({ ...s, loading: true, error: null, llmLoading: false, llmRequested: false }));
    try {
      const data = await api.getDocAnalysis(docId);
      setState({
        data,
        loading: false,
        error: null,
        offline: false,
        llmLoading: false,
        llmRequested: false,
      });
    } catch {
      // Demo fallback. Prefer a hand-authored fixture; otherwise synthesize a
      // complete, plausible analysis so the panel is always fully populated
      // offline (the demo never shows an empty "no analysis" state).
      const fixture = fixtureDocAnalysis[docId] ?? synthesizeDocAnalysis(docId, node);
      setState({
        data: fixture,
        loading: false,
        error: null,
        offline: true,
        llmLoading: false,
        llmRequested: false,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId, nodeKey]);

  useEffect(() => {
    load();
  }, [load]);

  /** Opt-in LLM enhancement (?llm=true). Never throws to the caller. */
  const explainWithAi = useCallback(async () => {
    if (!docId) return;
    setState((s) => ({ ...s, llmLoading: true }));
    try {
      const data = await api.getDocAnalysis(docId, { llm: true });
      setState((s) => ({ ...s, data, offline: false, llmLoading: false, llmRequested: true }));
    } catch {
      // Offline / Azure unconfigured: deterministic fixtures carry `llm: null`,
      // so we just flip to the "no AI notes" state rather than surfacing an error.
      setState((s) => ({ ...s, llmLoading: false, llmRequested: true }));
    }
  }, [docId]);

  return { ...state, refetch: load, explainWithAi };
}
