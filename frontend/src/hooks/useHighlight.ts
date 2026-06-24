import { useState, useCallback, useRef } from 'react';
import type { GraphHighlightEvent } from '../lib/types';

interface HighlightState {
  nodeIds: Set<string>;
  edgeIds: Set<string>;
  intensity: number;
  reason: GraphHighlightEvent['reason'] | null;
}

const EMPTY: HighlightState = {
  nodeIds: new Set(),
  edgeIds: new Set(),
  intensity: 0,
  reason: null,
};

export function useHighlight() {
  const [highlight, setHighlight] = useState<HighlightState>(EMPTY);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const emit = useCallback((event: GraphHighlightEvent) => {
    if (timerRef.current) clearTimeout(timerRef.current);

    setHighlight({
      nodeIds: new Set(event.nodeIds),
      edgeIds: new Set(event.edgeIds ?? []),
      intensity: event.intensity,
      reason: event.reason,
    });

    timerRef.current = setTimeout(() => {
      setHighlight(EMPTY);
    }, event.ttlMs);
  }, []);

  const clear = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setHighlight(EMPTY);
  }, []);

  return { highlight, emit, clear };
}

export type { HighlightState };
