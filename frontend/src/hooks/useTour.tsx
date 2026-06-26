import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { tourSteps } from '../lib/tourSteps';
import type { TourStep } from '../lib/tourSteps';

/**
 * First-run onboarding controller. On a user's first visit it pops a short welcome
 * (offering a guided coach-mark tour or the auto-pilot demo); afterwards it stays
 * out of the way. Re-openable any time from the header Help button. The
 * "seen it" flag is persisted in localStorage so it only auto-shows once.
 */
type TourPhase = 'off' | 'welcome' | 'steps';

interface TourContextValue {
  phase: TourPhase;
  index: number;
  total: number;
  step: TourStep | null;
  /** Welcome → start the coach-mark sequence. */
  beginTour: () => void;
  /** Re-open the welcome card (header Help button). */
  openWelcome: () => void;
  next: () => void;
  prev: () => void;
  /** Dismiss everything and remember it. */
  skip: () => void;
}

const STORAGE_KEY = 'dg.onboarded.v1';

const noop = () => {};
const defaultValue: TourContextValue = {
  phase: 'off',
  index: 0,
  total: tourSteps.length,
  step: null,
  beginTour: noop,
  openWelcome: noop,
  next: noop,
  prev: noop,
  skip: noop,
};

const TourContext = createContext<TourContextValue>(defaultValue);

// eslint-disable-next-line react-refresh/only-export-components
export const useTour = () => useContext(TourContext);

function hasOnboarded(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function markOnboarded() {
  try {
    window.localStorage.setItem(STORAGE_KEY, '1');
  } catch {
    /* ignore (private mode) */
  }
}

export function TourProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<TourPhase>('off');
  const [index, setIndex] = useState(0);

  const openWelcome = useCallback(() => {
    setIndex(0);
    setPhase('welcome');
  }, []);

  const beginTour = useCallback(() => {
    setIndex(0);
    setPhase('steps');
  }, []);

  const skip = useCallback(() => {
    setPhase('off');
    setIndex(0);
    markOnboarded();
  }, []);

  const next = useCallback(() => {
    setIndex((i) => {
      if (i >= tourSteps.length - 1) {
        setPhase('off');
        markOnboarded();
        return 0;
      }
      return i + 1;
    });
  }, []);

  const prev = useCallback(() => {
    setIndex((i) => Math.max(0, i - 1));
  }, []);

  // Auto-show the welcome once for first-time users — unless the auto-pilot demo
  // was explicitly requested via ?demo=1 (the demo owns the screen in that case).
  useEffect(() => {
    let demoParam = false;
    try {
      demoParam = new URLSearchParams(window.location.search).get('demo') === '1';
    } catch {
      /* ignore */
    }
    if (demoParam || hasOnboarded()) return;
    const t = window.setTimeout(() => setPhase('welcome'), 700);
    return () => window.clearTimeout(t);
  }, []);

  // Keyboard controls while the coach-mark sequence is showing.
  useEffect(() => {
    if (phase !== 'steps') return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        skip();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        next();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prev();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [phase, next, prev, skip]);

  const value: TourContextValue = {
    phase,
    index,
    total: tourSteps.length,
    step: phase === 'steps' ? tourSteps[index] ?? null : null,
    beginTour,
    openWelcome,
    next,
    prev,
    skip,
  };

  return <TourContext.Provider value={value}>{children}</TourContext.Provider>;
}
