import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { X, ChevronRight, ChevronLeft, Sparkles } from 'lucide-react';

/**
 * A reusable coach-mark overlay. It dims the screen, cuts a glowing window around
 * the UI region identified by `data-tour="<anchor>"`, and shows a callout next to
 * it. Used two ways:
 *  - **Interactive** (welcome tour): the callout carries title/body + Back/Next/Skip.
 *  - **autoMode** (guided demo): highlight-only, non-blocking, and sits *below* the
 *    demo caption/control bar so the auto-pilot keeps driving — the demo caption
 *    supplies the words, this just points at the region in use.
 */
interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface SpotlightOverlayProps {
  anchor: string;
  title?: string;
  body?: string;
  step?: number;
  total?: number;
  nextLabel?: string;
  /** Highlight-only, non-blocking, lower z-index (for the auto-pilot demo). */
  autoMode?: boolean;
  onNext?: () => void;
  onBack?: () => void;
  onSkip?: () => void;
}

function readRect(anchor: string): Rect | null {
  if (!anchor) return null;
  const el = document.querySelector(`[data-tour="${anchor}"]`);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  if (r.width === 0 && r.height === 0) return null;
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

const ghostBtn: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  cursor: 'pointer',
  color: '#94a3b8',
  fontSize: 12,
  fontWeight: 600,
  padding: '6px 10px',
};

const primaryBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 5,
  padding: '7px 14px',
  borderRadius: 8,
  background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
  border: 'none',
  cursor: 'pointer',
  color: 'white',
  fontSize: 12,
  fontWeight: 700,
  boxShadow: '0 0 14px rgba(139,92,246,0.4)',
};

const secondaryBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '7px 12px',
  borderRadius: 8,
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(139,92,246,0.2)',
  cursor: 'pointer',
  color: '#cbd5e1',
  fontSize: 12,
  fontWeight: 600,
};

export function SpotlightOverlay({
  anchor,
  title,
  body,
  step,
  total,
  nextLabel,
  autoMode,
  onNext,
  onBack,
  onSkip,
}: SpotlightOverlayProps) {
  const [rect, setRect] = useState<Rect | null>(() => readRect(anchor));
  const calloutRef = useRef<HTMLDivElement>(null);
  const [calloutH, setCalloutH] = useState(180);

  // Track the target rect on mount, when the anchor changes, and on resize/scroll
  // (an extra rAF + short timeout lets panel open/resize animations settle).
  useEffect(() => {
    const update = () => setRect(readRect(anchor));
    update();
    const raf = requestAnimationFrame(update);
    const t = window.setTimeout(update, 140);
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(t);
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
    };
  }, [anchor]);

  useLayoutEffect(() => {
    if (calloutRef.current) setCalloutH(calloutRef.current.offsetHeight);
  }, [title, body, rect]);

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const pad = 8;
  const calloutW = Math.min(360, vw - 32);

  let calloutTop: number;
  let calloutLeft: number;
  if (rect) {
    const belowSpace = vh - (rect.top + rect.height);
    const placeBelow = belowSpace >= calloutH + 24 || belowSpace >= rect.top;
    calloutTop = placeBelow
      ? rect.top + rect.height + 14
      : Math.max(16, rect.top - calloutH - 14);
    calloutLeft = Math.min(
      Math.max(16, rect.left + rect.width / 2 - calloutW / 2),
      Math.max(16, vw - calloutW - 16),
    );
  } else {
    calloutTop = vh / 2 - calloutH / 2;
    calloutLeft = vw / 2 - calloutW / 2;
  }

  const dim = autoMode ? 0.5 : 0.72;
  const isLast = step != null && total != null && step >= total;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: autoMode ? 900 : 1400,
        pointerEvents: autoMode ? 'none' : 'auto',
      }}
    >
      {rect ? (
        <div
          style={{
            position: 'absolute',
            top: rect.top - pad,
            left: rect.left - pad,
            width: rect.width + pad * 2,
            height: rect.height + pad * 2,
            borderRadius: 12,
            boxShadow: `0 0 0 9999px rgba(8,8,12,${dim})`,
            border: '2px solid rgba(139,92,246,0.9)',
            transition: 'all 0.35s cubic-bezier(0.22,1,0.36,1)',
            pointerEvents: 'none',
          }}
        />
      ) : (
        !autoMode && (
          <div style={{ position: 'absolute', inset: 0, background: `rgba(8,8,12,${dim})` }} />
        )
      )}

      {!autoMode && (title || body) && (
        <div
          ref={calloutRef}
          className="glass-panel-elevated animate-fade-in-up"
          style={{
            position: 'absolute',
            top: calloutTop,
            left: calloutLeft,
            width: calloutW,
            padding: '16px 18px',
            borderRadius: 14,
            border: '1px solid rgba(139,92,246,0.4)',
            background: 'rgba(13,13,18,0.96)',
            boxShadow: '0 16px 50px rgba(0,0,0,0.55), 0 0 30px rgba(139,92,246,0.2)',
            pointerEvents: 'auto',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Sparkles size={13} color="#a78bfa" />
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: '#a78bfa',
              }}
            >
              Quick tour{step != null && total != null ? ` · ${step} / ${total}` : ''}
            </span>
            {onSkip && (
              <button
                onClick={onSkip}
                title="Close (Esc)"
                style={{
                  marginLeft: 'auto',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#64748b',
                  display: 'flex',
                  padding: 2,
                }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          {title && (
            <div style={{ fontSize: 16, lineHeight: 1.4, color: '#f1f5f9', fontWeight: 700, marginBottom: 6 }}>
              {title}
            </div>
          )}
          {body && <div style={{ fontSize: 13, lineHeight: 1.55, color: '#94a3b8' }}>{body}</div>}

          {(onNext || onBack) && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14 }}>
              {onBack && step != null && step > 1 && (
                <button onClick={onBack} style={secondaryBtn}>
                  <ChevronLeft size={13} /> Back
                </button>
              )}
              <div style={{ flex: 1 }} />
              {onSkip && (
                <button onClick={onSkip} style={ghostBtn}>
                  Skip
                </button>
              )}
              {onNext && (
                <button onClick={onNext} style={primaryBtn}>
                  {nextLabel ?? (isLast ? 'Done' : 'Next')} <ChevronRight size={13} />
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
