import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import type { MetricsDTO } from '../lib/types';
import { demoScript } from '../lib/demoScript';

/**
 * Auto-pilot "Presenter Mode" engine.
 *
 * Drives the app's own handlers through a scripted storyline so the presenter can
 * just talk. Everything is gated on `active` — when the demo is off this provider
 * is inert and the app behaves exactly as normal. The storyline lives in
 * `lib/demoScript.ts`; components register driver callbacks via `registerDriver`.
 */

export type DemoAction =
  | { kind: 'caption' }
  | { kind: 'selectDoc'; docId: string }
  | { kind: 'chat'; text: string }
  | { kind: 'highlight'; nodeIds: string[]; focus?: boolean; intensity?: number }
  | { kind: 'clearHighlight' }
  | { kind: 'openInsights'; tab: 'corpus' | 'doc' }
  | { kind: 'closeInsights' }
  | { kind: 'propose'; docId?: string }
  | { kind: 'approve'; metricsDelta?: Partial<MetricsDTO> };

export interface DemoBeat {
  id: string;
  /** Teleprompter line shown on screen (doubles as the talking-point cue). */
  caption: string;
  /** Optional extra presenter note (smaller, muted). */
  cue?: string;
  action: DemoAction;
  /** Autoplay dwell before advancing to the next beat. */
  durationMs?: number;
}

export interface DemoDriver {
  selectDoc: (docId: string) => void;
  highlight: (nodeIds: string[], opts?: { focus?: boolean; intensity?: number }) => void;
  clearHighlight: () => void;
  openInsights: (tab: 'corpus' | 'doc') => void;
  closeInsights: () => void;
  propose: (docId?: string) => void;
  approve: () => void;
}

/** A one-shot command for the chat panel to type + send (nonce makes replays fire). */
export interface ChatCommand {
  text: string;
  nonce: number;
}

interface DemoContextValue {
  active: boolean;
  playing: boolean;
  index: number;
  total: number;
  current: DemoBeat | null;
  next_: DemoBeat | null;
  chatCommand: ChatCommand | null;
  metricsDelta: Partial<MetricsDTO>;
  start: () => void;
  exit: () => void;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  next: () => void;
  prev: () => void;
  restart: () => void;
  goTo: (i: number) => void;
  captionsVisible: boolean;
  toggleCaptions: () => void;
  registerDriver: (d: Partial<DemoDriver>) => void;
}

const DEFAULT_DURATION = 6500;

const noop = () => {};
const defaultValue: DemoContextValue = {
  active: false,
  playing: false,
  index: 0,
  total: demoScript.length,
  current: null,
  next_: null,
  chatCommand: null,
  metricsDelta: {},
  start: noop,
  exit: noop,
  play: noop,
  pause: noop,
  toggle: noop,
  next: noop,
  prev: noop,
  restart: noop,
  goTo: noop,
  captionsVisible: true,
  toggleCaptions: noop,
  registerDriver: noop,
};

const DemoContext = createContext<DemoContextValue>(defaultValue);

// eslint-disable-next-line react-refresh/only-export-components
export const useDemo = () => useContext(DemoContext);

function mergeDelta(
  base: Partial<MetricsDTO>,
  add: Partial<MetricsDTO>,
): Partial<MetricsDTO> {
  const out = { ...base } as Record<string, number>;
  for (const k of Object.keys(add)) {
    out[k] = (out[k] ?? 0) + ((add as Record<string, number>)[k] ?? 0);
  }
  return out as Partial<MetricsDTO>;
}

export function DemoProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [index, setIndex] = useState(0);
  const [chatCommand, setChatCommand] = useState<ChatCommand | null>(null);
  const [metricsDelta, setMetricsDelta] = useState<Partial<MetricsDTO>>({});
  const [captionsVisible, setCaptionsVisible] = useState(true);

  const driverRef = useRef<Partial<DemoDriver>>({});
  const prevIndexRef = useRef<number>(-1);
  const nonceRef = useRef(0);

  const registerDriver = useCallback((d: Partial<DemoDriver>) => {
    driverRef.current = { ...driverRef.current, ...d };
  }, []);

  // Perform a beat's side effect. Heavy / one-shot actions (chat, propose,
  // approve) only fire when moving forward, so stepping back is non-destructive.
  const applyBeat = useCallback((i: number, forward: boolean) => {
    const beat = demoScript[i];
    if (!beat) return;
    const d = driverRef.current;
    const a = beat.action;
    switch (a.kind) {
      case 'selectDoc':
        d.selectDoc?.(a.docId);
        break;
      case 'highlight':
        d.highlight?.(a.nodeIds, { focus: a.focus, intensity: a.intensity });
        break;
      case 'clearHighlight':
        d.clearHighlight?.();
        break;
      case 'openInsights':
        d.openInsights?.(a.tab);
        break;
      case 'closeInsights':
        d.closeInsights?.();
        break;
      case 'chat':
        if (forward) {
          nonceRef.current += 1;
          setChatCommand({ text: a.text, nonce: nonceRef.current });
        }
        break;
      case 'propose':
        if (forward) d.propose?.(a.docId);
        break;
      case 'approve':
        if (forward) {
          d.approve?.();
          if (a.metricsDelta) setMetricsDelta((m) => mergeDelta(m, a.metricsDelta!));
        }
        break;
      case 'caption':
      default:
        break;
    }
  }, []);

  // Run the active beat whenever the index changes (or the demo turns on).
  useEffect(() => {
    if (!active) return;
    const forward = index >= prevIndexRef.current;
    prevIndexRef.current = index;
    applyBeat(index, forward);
  }, [index, active, applyBeat]);

  // Autoplay timer (paused via `playing`).
  useEffect(() => {
    if (!active || !playing) return;
    if (index >= demoScript.length - 1) {
      setPlaying(false);
      return;
    }
    const ms = demoScript[index]?.durationMs ?? DEFAULT_DURATION;
    const t = window.setTimeout(
      () => setIndex((i) => Math.min(i + 1, demoScript.length - 1)),
      ms,
    );
    return () => window.clearTimeout(t);
  }, [active, playing, index]);

  const start = useCallback(() => {
    prevIndexRef.current = -1;
    setMetricsDelta({});
    setChatCommand(null);
    setCaptionsVisible(true);
    setIndex(0);
    setActive(true);
    setPlaying(true);
  }, []);

  const exit = useCallback(() => {
    setActive(false);
    setPlaying(false);
    setIndex(0);
    setChatCommand(null);
    setMetricsDelta({});
    prevIndexRef.current = -1;
    driverRef.current.clearHighlight?.();
    driverRef.current.closeInsights?.();
  }, []);

  const play = useCallback(() => setPlaying(true), []);
  const pause = useCallback(() => setPlaying(false), []);
  const toggle = useCallback(() => setPlaying((p) => !p), []);
  const next = useCallback(() => {
    setPlaying(false);
    setIndex((i) => Math.min(i + 1, demoScript.length - 1));
  }, []);
  const prev = useCallback(() => {
    setPlaying(false);
    setIndex((i) => Math.max(i - 1, 0));
  }, []);
  const restart = useCallback(() => {
    prevIndexRef.current = -1;
    setMetricsDelta({});
    setChatCommand(null);
    setIndex(0);
    setPlaying(true);
  }, []);
  const goTo = useCallback((i: number) => {
    setPlaying(false);
    setIndex(Math.max(0, Math.min(i, demoScript.length - 1)));
  }, []);

  const toggleCaptions = useCallback(() => setCaptionsVisible((v) => !v), []);

  // Keyboard controls while the demo is active.
  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        exit();
        return;
      }
      const el = document.activeElement;
      const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA');
      if (typing) return; // don't hijack keys while a field is focused
      if (e.key === ' ') {
        e.preventDefault();
        toggle();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        next();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prev();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        restart();
      } else if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        toggleCaptions();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active, toggle, next, prev, restart, exit, toggleCaptions]);

  // Optional auto-start via ?demo=1.
  useEffect(() => {
    try {
      if (new URLSearchParams(window.location.search).get('demo') === '1') start();
    } catch {
      /* ignore */
    }
  }, [start]);

  const value: DemoContextValue = {
    active,
    playing,
    index,
    total: demoScript.length,
    current: demoScript[index] ?? null,
    next_: demoScript[index + 1] ?? null,
    chatCommand,
    metricsDelta,
    start,
    exit,
    play,
    pause,
    toggle,
    next,
    prev,
    restart,
    goTo,
    captionsVisible,
    toggleCaptions,
    registerDriver,
  };

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}
