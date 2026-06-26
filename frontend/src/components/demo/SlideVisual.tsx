import {
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Quote,
  Plus,
  Minus,
  Lock,
  Terminal,
  Plug,
} from 'lucide-react';
import type { SlideVisual as SlideVisualData } from '../../hooks/useDemo';

/**
 * Renders the optional "proof" artifact on an act slide — a small, concrete
 * example that *shows* the bullets' claim (evidence, not assertion). Pure
 * presentation: every value comes from the demo script (which mirrors the
 * fixtures), so the preview matches what the live beats then show.
 */

const GOOD = { fg: '#34d399', bg: 'rgba(34,211,160,0.12)', bd: 'rgba(34,211,160,0.32)' };
const BAD = { fg: '#f87171', bg: 'rgba(239,68,68,0.12)', bd: 'rgba(239,68,68,0.32)' };
const surface = 'rgba(255,255,255,0.04)';
const surfaceBorder = '1px solid rgba(139,92,246,0.16)';

function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

function ConfidencePill({ value }: { value: number }) {
  const strong = value >= 0.7;
  const tone = strong ? GOOD : { fg: '#fbbf24', bg: 'rgba(251,191,36,0.12)', bd: 'rgba(251,191,36,0.32)' };
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 9px',
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 700,
        color: tone.fg,
        background: tone.bg,
        border: `1px solid ${tone.bd}`,
        whiteSpace: 'nowrap',
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      <ShieldCheck size={12} /> confidence {pct(value)}
    </span>
  );
}

function ConflictView({ v }: { v: Extract<SlideVisualData, { kind: 'conflict' }> }) {
  const Card = ({ side }: { side: typeof v.left }) => {
    const tone = side.tone === 'good' ? GOOD : BAD;
    return (
      <div
        style={{
          flex: 1,
          minWidth: 0,
          background: surface,
          border: `1px solid ${tone.bd}`,
          borderRadius: 12,
          padding: '12px 13px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9 }}>
          <code style={{ fontSize: 12, color: '#e2e8f0', fontWeight: 700 }}>{side.title}</code>
          <span
            style={{
              marginLeft: 'auto',
              fontSize: 9.5,
              fontWeight: 800,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              color: tone.fg,
              background: tone.bg,
              border: `1px solid ${tone.bd}`,
              borderRadius: 6,
              padding: '2px 7px',
            }}
          >
            {side.badge}
          </span>
        </div>
        {side.lines.map((l, i) => (
          <div
            key={i}
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
              fontSize: 12,
              lineHeight: 1.6,
              color: '#cbd5e1',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {l}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', alignItems: 'stretch', gap: 10 }}>
      <Card side={v.left} />
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '4px 8px',
            borderRadius: 999,
            background: BAD.bg,
            border: `1px solid ${BAD.bd}`,
            color: BAD.fg,
            fontSize: 10,
            fontWeight: 800,
            whiteSpace: 'nowrap',
            boxShadow: '0 0 16px rgba(239,68,68,0.25)',
          }}
        >
          <AlertTriangle size={12} /> {v.relation}
        </div>
      </div>
      <Card side={v.right} />
    </div>
  );
}

function AnswerView({ v }: { v: Extract<SlideVisualData, { kind: 'answer' }> }) {
  return (
    <div style={{ background: surface, border: surfaceBorder, borderRadius: 12, padding: '13px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9 }}>
        <Quote size={13} color="#a78bfa" />
        <span style={{ fontSize: 12.5, color: '#94a3b8', fontStyle: 'italic' }}>"{v.question}"</span>
      </div>
      <div style={{ fontSize: 13.5, lineHeight: 1.5, color: '#e2e8f0', marginBottom: 12 }}>{v.answer}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {v.citations.map((c) => (
          <span
            key={c.label}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '3px 9px',
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 600,
              color: '#cbd5e1',
              background: 'rgba(139,92,246,0.12)',
              border: '1px solid rgba(139,92,246,0.3)',
            }}
          >
            <code style={{ fontSize: 11, color: '#e2e8f0' }}>{c.label}</code>
            <span style={{ color: '#a78bfa', fontVariantNumeric: 'tabular-nums' }}>{pct(c.relevance)}</span>
          </span>
        ))}
        <div style={{ flex: 1 }} />
        <ConfidencePill value={v.confidence} />
      </div>
    </div>
  );
}

function DiffView({ v }: { v: Extract<SlideVisualData, { kind: 'diff' }> }) {
  const Row = ({ sign, text }: { sign: '+' | '-'; text: string }) => {
    const tone = sign === '+' ? GOOD : BAD;
    const Icon = sign === '+' ? Plus : Minus;
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '4px 10px',
          background: tone.bg,
          borderLeft: `2px solid ${tone.bd}`,
        }}
      >
        <Icon size={12} color={tone.fg} style={{ flexShrink: 0 }} />
        <code
          style={{
            fontSize: 12,
            color: '#cbd5e1',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {text}
        </code>
      </div>
    );
  };
  return (
    <div>
      <div style={{ background: surface, border: surfaceBorder, borderRadius: 12, overflow: 'hidden' }}>
        {v.before.map((l, i) => (
          <Row key={`b${i}`} sign="-" text={l} />
        ))}
        {v.after.map((l, i) => (
          <Row key={`a${i}`} sign="+" text={l} />
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 11, flexWrap: 'wrap' }}>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 9px',
            borderRadius: 999,
            fontSize: 11,
            fontWeight: 700,
            color: '#a78bfa',
            background: 'rgba(139,92,246,0.12)',
            border: '1px solid rgba(139,92,246,0.3)',
          }}
        >
          <ShieldCheck size={12} /> {v.reviewer}
        </span>
        <ConfidencePill value={v.confidence} />
        <div style={{ flex: 1 }} />
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 10px',
            borderRadius: 999,
            fontSize: 11,
            fontWeight: 700,
            color: '#fbbf24',
            background: 'rgba(251,191,36,0.12)',
            border: '1px solid rgba(251,191,36,0.32)',
            whiteSpace: 'nowrap',
          }}
        >
          {v.status}
        </span>
      </div>
    </div>
  );
}

function StatsView({ v }: { v: Extract<SlideVisualData, { kind: 'stats' }> }) {
  return (
    <div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {v.items.map((s) => {
          const good = s.tone === 'good';
          return (
            <div
              key={s.label}
              style={{
                flex: '1 1 120px',
                minWidth: 0,
                background: good ? GOOD.bg : surface,
                border: `1px solid ${good ? GOOD.bd : 'rgba(139,92,246,0.16)'}`,
                borderRadius: 12,
                padding: '12px 14px',
              }}
            >
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  letterSpacing: '-0.02em',
                  color: good ? GOOD.fg : '#f1f5f9',
                  fontVariantNumeric: 'tabular-nums',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {good && <ArrowRight size={16} style={{ transform: 'rotate(-45deg)' }} />}
                {s.value}
              </div>
              <div style={{ fontSize: 11.5, color: '#94a3b8', marginTop: 3 }}>{s.label}</div>
            </div>
          );
        })}
      </div>
      {v.footnote && (
        <div style={{ fontSize: 11.5, color: '#64748b', marginTop: 11, textAlign: 'center' }}>{v.footnote}</div>
      )}
    </div>
  );
}

function PermissionView({ v }: { v: Extract<SlideVisualData, { kind: 'permission' }> }) {
  const LOCK = { fg: '#94a3b8', bg: 'rgba(148,163,184,0.10)', bd: 'rgba(148,163,184,0.28)' };
  const lines = v.redactedLines ?? 3;
  const widths = ['78%', '92%', '64%', '85%', '70%'];
  return (
    <div style={{ background: surface, border: `1px solid ${LOCK.bd}`, borderRadius: 12, padding: '13px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Lock size={14} color={LOCK.fg} />
        <code style={{ fontSize: 12, color: '#cbd5e1', fontWeight: 700 }}>{v.docTitle}</code>
        <span
          style={{
            marginLeft: 'auto',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: LOCK.fg,
            background: LOCK.bg,
            border: `1px solid ${LOCK.bd}`,
            borderRadius: 6,
            padding: '2px 8px',
          }}
        >
          <Lock size={10} /> {v.badge}
        </span>
      </div>

      {/* Permission fog: the node exists, but its content is never shown. */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, filter: 'blur(0.5px)', opacity: 0.55 }}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            style={{
              height: 9,
              width: widths[i % widths.length],
              borderRadius: 5,
              background: 'linear-gradient(90deg, rgba(148,163,184,0.35), rgba(148,163,184,0.12))',
            }}
          />
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 12, fontSize: 12, color: '#94a3b8' }}>
        <ShieldCheck size={13} color="#a78bfa" style={{ flexShrink: 0 }} />
        <span>{v.note}</span>
      </div>
    </div>
  );
}

function McpView({ v }: { v: Extract<SlideVisualData, { kind: 'mcp' }> }) {
  return (
    <div style={{ background: 'rgba(2,6,12,0.6)', border: surfaceBorder, borderRadius: 12, overflow: 'hidden' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 7,
          padding: '8px 12px',
          borderBottom: surfaceBorder,
          background: 'rgba(255,255,255,0.03)',
        }}
      >
        <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ef4444' }} />
        <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#f59e0b' }} />
        <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#22c55e' }} />
        <span
          style={{
            marginLeft: 6,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            fontSize: 11,
            color: '#94a3b8',
            fontWeight: 600,
          }}
        >
          <Terminal size={12} /> {v.client}
        </span>
      </div>
      <div style={{ padding: '12px 14px', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9, flexWrap: 'wrap' }}>
          <span style={{ color: '#a78bfa', fontWeight: 700, fontSize: 12 }}>@docguardian</span>
          <span style={{ color: '#cbd5e1', fontSize: 12 }}>{v.prompt}</span>
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 11 }}>
          <ArrowRight size={14} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
          <span style={{ color: '#e2e8f0', fontSize: 12.5, lineHeight: 1.5 }}>{v.answer}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {v.citations.map((c) => (
            <span
              key={c}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '3px 9px',
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 600,
                color: '#cbd5e1',
                background: 'rgba(139,92,246,0.12)',
                border: '1px solid rgba(139,92,246,0.3)',
              }}
            >
              {c}
            </span>
          ))}
          <div style={{ flex: 1 }} />
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              padding: '3px 9px',
              borderRadius: 999,
              fontSize: 10.5,
              fontWeight: 700,
              color: GOOD.fg,
              background: GOOD.bg,
              border: `1px solid ${GOOD.bd}`,
              whiteSpace: 'nowrap',
            }}
          >
            <Plug size={11} /> via DocGuardian MCP
          </span>
        </div>
      </div>
    </div>
  );
}

export function SlideVisual({ visual }: { visual: SlideVisualData }) {
  switch (visual.kind) {
    case 'conflict':
      return <ConflictView v={visual} />;
    case 'answer':
      return <AnswerView v={visual} />;
    case 'diff':
      return <DiffView v={visual} />;
    case 'stats':
      return <StatsView v={visual} />;
    case 'permission':
      return <PermissionView v={visual} />;
    case 'mcp':
      return <McpView v={visual} />;
    default:
      return null;
  }
}
