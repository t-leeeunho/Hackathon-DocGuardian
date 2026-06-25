import { useCallback, useEffect, useState } from 'react';

/**
 * A panel width that persists across reloads and clamps to [min, max].
 *
 * `resize(delta)` nudges the width by a pixel delta (from a drag handle);
 * `reset()` restores the default (used on handle double-click).
 */
export function usePanelWidth(key: string, def: number, min: number, max: number) {
  const storageKey = `dg.width.${key}`;

  const [width, setWidth] = useState<number>(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      const n = raw != null ? Number(raw) : NaN;
      if (Number.isFinite(n)) return Math.min(max, Math.max(min, n));
    } catch {
      /* localStorage unavailable — fall back to default */
    }
    return def;
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, String(width));
    } catch {
      /* ignore persistence failures */
    }
  }, [storageKey, width]);

  const resize = useCallback(
    (delta: number) => setWidth((w) => Math.min(max, Math.max(min, w + delta))),
    [min, max],
  );

  const reset = useCallback(() => setWidth(def), [def]);

  return { width, resize, reset, setWidth };
}
