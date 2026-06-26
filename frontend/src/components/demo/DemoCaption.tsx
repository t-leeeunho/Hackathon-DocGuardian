import { Sparkles, EyeOff, ChevronRight, ChevronLeft } from 'lucide-react';
import { useDemo } from '../../hooks/useDemo';

/**
 * Teleprompter overlay — the current beat's caption (the talking-point cue) plus
 * Back / Next controls so the whole presentation+demo advances by clicking one
 * button. Hidden for `slide` beats (those render the full-screen DemoSlide) and
 * inert unless the demo is active.
 */
export function DemoCaption() {
  const {
    active,
    current,
    next_,
    index,
    total,
    captionsVisible,
    toggleCaptions,
    next,
    prev,
    exit,
  } = useDemo();
  if (!active || !current || !captionsVisible) return null;
  if (current.action.kind === 'slide') return null;

  const isLast = index >= total - 1;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 96,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(760px, calc(100vw - 48px))',
        zIndex: 1000,
        pointerEvents: 'none',
      }}
    >
      <div
        className="glass-panel-elevated animate-fade-in-up"
        style={{
          padding: '16px 20px',
          borderRadius: 14,
          border: '1px solid rgba(139,92,246,0.35)',
          boxShadow: '0 12px 40px rgba(0,0,0,0.5), 0 0 30px rgba(139,92,246,0.18)',
          background: 'rgba(13,13,18,0.92)',
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
            Guided demo · {index + 1} / {total}
          </span>
          <button
            onClick={toggleCaptions}
            title="Hide captions (C)"
            style={{
              marginLeft: 'auto',
              pointerEvents: 'auto',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#64748b',
              padding: 2,
              borderRadius: 4,
              display: 'flex',
            }}
          >
            <EyeOff size={14} />
          </button>
        </div>

        <div style={{ fontSize: 18, lineHeight: 1.45, color: '#f1f5f9', fontWeight: 600 }}>
          {current.caption}
        </div>

        {current.cue && (
          <div style={{ fontSize: 13, lineHeight: 1.5, color: '#94a3b8', marginTop: 6 }}>
            {current.cue}
          </div>
        )}

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 12,
            paddingTop: 10,
            borderTop: '1px solid rgba(139,92,246,0.12)',
            pointerEvents: 'auto',
          }}
        >
          {index > 0 && (
            <button
              onClick={prev}
              title="Back (←)"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 3,
                padding: '6px 11px',
                borderRadius: 8,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(139,92,246,0.2)',
                cursor: 'pointer',
                color: '#cbd5e1',
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              <ChevronLeft size={13} /> Back
            </button>
          )}

          {next_ && (
            <div
              style={{
                fontSize: 11,
                color: '#475569',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                flex: 1,
                minWidth: 0,
              }}
            >
              <span style={{ color: '#64748b', fontWeight: 600 }}>Next · </span>
              {next_.action.kind === 'slide' ? next_.action.title : next_.caption}
            </div>
          )}
          <div style={{ flex: next_ ? 0 : 1 }} />

          <button
            onClick={isLast ? exit : next}
            title="Next (→)"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '7px 15px',
              borderRadius: 8,
              background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
              border: 'none',
              cursor: 'pointer',
              color: 'white',
              fontSize: 12,
              fontWeight: 700,
              boxShadow: '0 0 14px rgba(139,92,246,0.4)',
            }}
          >
            {isLast ? 'Finish' : 'Next'} <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
