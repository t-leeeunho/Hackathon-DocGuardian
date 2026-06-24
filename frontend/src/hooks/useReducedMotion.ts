import React, { useEffect, useState } from 'react';

export function useReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  return mq.matches;
}

export function useReducedMotionLive(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  return reduced;
}

// suppress unused import warning
void React;
