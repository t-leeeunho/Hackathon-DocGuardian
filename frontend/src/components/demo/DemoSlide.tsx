import { Sparkles, ChevronRight, ChevronLeft } from 'lucide-react';
import { useDemo } from '../../hooks/useDemo';
import { SlideVisual } from './SlideVisual';

/**
 * Full-screen "mini-presentation" slide for the guided demo. Shown for `slide`
 * beats (the start of each act) — a kicker, a headline and a few bullets, with
 * a prominent Next so the whole presentation+demo runs by clicking one button.
 */
const primaryBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '10px 20px',
  borderRadius: 10,
  background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
  border: 'none',
  cursor: 'pointer',
  color: 'white',
  fontSize: 14,
  fontWeight: 700,
  boxShadow: '0 0 18px rgba(139,92,246,0.45)',
};

const secondaryBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '10px 14px',
  borderRadius: 10,
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(139,92,246,0.2)',
  cursor: 'pointer',
  color: '#cbd5e1',
  fontSize: 13,
  fontWeight: 600,
};

export function DemoSlide() {
  const { active, current, index, total, next, prev, exit } = useDemo();
  if (!active || !current || current.action.kind !== 'slide') return null;

  const a = current.action;
  const isLast = index >= total - 1;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(8,8,12,0.84)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        className="glass-panel-elevated animate-fade-in-up"
        style={{
          width: 'min(680px, 100%)',
          maxHeight: 'calc(100vh - 48px)',
          overflowY: 'auto',
          padding: '32px 36px',
          borderRadius: 20,
          border: '1px solid rgba(139,92,246,0.4)',
          background: 'rgba(13,13,18,0.97)',
          boxShadow: '0 28px 80px rgba(0,0,0,0.62), 0 0 44px rgba(139,92,246,0.18)',
        }}
      >
        {a.kicker && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <Sparkles size={14} color="#a78bfa" />
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: '#a78bfa',
              }}
            >
              {a.kicker}
            </span>
          </div>
        )}

        <div
          style={{
            fontSize: 30,
            lineHeight: 1.2,
            fontWeight: 800,
            color: '#f1f5f9',
            letterSpacing: '-0.02em',
            marginBottom: 22,
          }}
        >
          {a.title}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 13, marginBottom: a.visual ? 22 : 30 }}>
          {a.bullets.map((b, i) => (
            <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
                  marginTop: 9,
                  flexShrink: 0,
                  boxShadow: '0 0 8px rgba(139,92,246,0.6)',
                }}
              />
              <span style={{ fontSize: 16, lineHeight: 1.5, color: '#cbd5e1' }}>{b}</span>
            </div>
          ))}
        </div>

        {a.visual && (
          <div style={{ marginBottom: 28 }}>
            <SlideVisual visual={a.visual} />
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {index > 0 && (
            <button onClick={prev} style={secondaryBtn}>
              <ChevronLeft size={15} /> Back
            </button>
          )}
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: '#475569', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
            {index + 1} / {total}
          </span>
          <button onClick={isLast ? exit : next} style={primaryBtn}>
            {isLast ? 'Finish' : 'Next'} <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
