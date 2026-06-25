import { Play, Pause, SkipBack, SkipForward, RotateCcw, X, Eye, EyeOff } from 'lucide-react';
import { useDemo } from '../../hooks/useDemo';

const iconBtn = (disabled?: boolean): React.CSSProperties => ({
  width: 34,
  height: 34,
  borderRadius: 8,
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(139,92,246,0.2)',
  cursor: disabled ? 'not-allowed' : 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: disabled ? '#3f4654' : '#cbd5e1',
  transition: 'all 0.15s',
});

/**
 * Floating transport controls for the guided demo: Prev / Play-Pause / Next,
 * Restart and Exit, plus a progress bar. Keyboard equivalents (Space, ←/→, R,
 * Esc) are handled by the demo engine. Inert unless the demo is active.
 */
export function DemoControlBar() {
  const { active, playing, index, total, play, pause, next, prev, restart, exit, captionsVisible, toggleCaptions } = useDemo();
  if (!active) return null;

  const atStart = index <= 0;
  const atEnd = index >= total - 1;
  const progress = total > 1 ? (index / (total - 1)) * 100 : 100;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1001,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        alignItems: 'center',
      }}
    >
      <div
        className="glass-panel-elevated"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 12px',
          borderRadius: 12,
          border: '1px solid rgba(139,92,246,0.35)',
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
          background: 'rgba(13,13,18,0.95)',
        }}
      >
        <button style={iconBtn(atStart)} onClick={prev} disabled={atStart} title="Previous (←)">
          <SkipBack size={15} />
        </button>

        <button
          onClick={playing ? pause : play}
          title={playing ? 'Pause (Space)' : 'Play (Space)'}
          style={{
            width: 40,
            height: 40,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: '0 0 14px rgba(139,92,246,0.45)',
          }}
        >
          {playing ? <Pause size={17} /> : <Play size={17} style={{ marginLeft: 2 }} />}
        </button>

        <button style={iconBtn(atEnd)} onClick={next} disabled={atEnd} title="Next (→)">
          <SkipForward size={15} />
        </button>

        <div style={{ width: 1, height: 22, background: 'rgba(139,92,246,0.2)', margin: '0 2px' }} />

        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: '#94a3b8',
            minWidth: 44,
            textAlign: 'center',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {index + 1} / {total}
        </span>

        <button
          style={{
            ...iconBtn(),
            color: captionsVisible ? '#cbd5e1' : '#a78bfa',
            background: captionsVisible ? 'rgba(255,255,255,0.05)' : 'rgba(139,92,246,0.15)',
          }}
          onClick={toggleCaptions}
          title={captionsVisible ? 'Hide captions (C)' : 'Show captions (C)'}
        >
          {captionsVisible ? <Eye size={14} /> : <EyeOff size={14} />}
        </button>

        <button style={iconBtn()} onClick={restart} title="Restart (R)">
          <RotateCcw size={14} />
        </button>

        <button
          onClick={exit}
          title="Exit demo (Esc)"
          style={{
            ...iconBtn(),
            background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.25)',
            color: '#fca5a5',
          }}
        >
          <X size={15} />
        </button>
      </div>

      {/* Progress bar */}
      <div
        style={{
          width: 320,
          height: 3,
          borderRadius: 2,
          background: 'rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progress}%`,
            borderRadius: 2,
            background: 'linear-gradient(90deg, #8b5cf6, #3b82f6)',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
    </div>
  );
}
