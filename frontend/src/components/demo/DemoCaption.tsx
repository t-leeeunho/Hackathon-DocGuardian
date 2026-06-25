import { Sparkles, EyeOff } from 'lucide-react';
import { useDemo } from '../../hooks/useDemo';

/**
 * Teleprompter overlay — the current beat's caption (the talking-point cue) plus
 * a small preview of what's next. Inert unless the demo is active, and hideable
 * (the small control bar stays so it can be brought back).
 */
export function DemoCaption() {
  const { active, current, next_, index, total, captionsVisible, toggleCaptions } = useDemo();
  if (!active || !current || !captionsVisible) return null;

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

        {next_ && (
          <div
            style={{
              fontSize: 11,
              color: '#475569',
              marginTop: 10,
              paddingTop: 8,
              borderTop: '1px solid rgba(139,92,246,0.12)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            <span style={{ color: '#64748b', fontWeight: 600 }}>Next · </span>
            {next_.caption}
          </div>
        )}
      </div>
    </div>
  );
}
