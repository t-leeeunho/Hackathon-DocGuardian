import { useEffect, useState } from 'react';
import {
  TrendingUp,
  BarChart3,
  CheckCircle2,
  ShieldCheck,
  FileText,
  GitBranch,
  AlertTriangle,
  Award,
} from 'lucide-react';
import { useTrends } from '../../hooks/useTrends';
import { useAnalysis } from '../../hooks/useAnalysis';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import type { DocRef, HistogramBucket, TrendPoint } from '../../lib/types';

interface TrendsPanelProps {
  /** Click a worst-offender row to focus that doc in the graph + detail panels. */
  onSelectDoc?: (docId: string) => void;
}

const GREEN = '#22d3a0';
const AMBER = '#f59e0b';
const VIOLET = '#8b5cf6';
const BLUE = '#3b82f6';
const RED = '#ef4444';

function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}
function basename(id: string): string {
  return id.split('/').pop() || id;
}
function shortDate(iso: string): string {
  // 'YYYY-MM-DD' -> 'MM-DD'
  return iso.length >= 10 ? iso.slice(5) : iso;
}
function qualityColor(score: number): string {
  return score >= 0.75 ? GREEN : score >= 0.5 ? AMBER : RED;
}

// --------------------------------------------------------------------------- //
// Layout helpers
// --------------------------------------------------------------------------- //
function SectionLabel({ icon, children }: { icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}>
      {icon}
      <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
        {children}
      </span>
    </div>
  );
}

function Kpi({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div
      style={{
        flex: '1 1 calc(50% - 4px)',
        minWidth: 110,
        padding: '10px 12px',
        borderRadius: 10,
        background: `${color}10`,
        border: `1px solid ${color}22`,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: 8,
          background: `${color}18`,
          border: `1px solid ${color}28`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 10, color: '#64748b', marginTop: 3 }}>{label}</div>
      </div>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: 12,
        borderRadius: 10,
        background: 'rgba(255,255,255,0.025)',
        border: '1px solid rgba(139,92,246,0.12)',
      }}
    >
      {children}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Inline SVG: detected-vs-fixed time series
// --------------------------------------------------------------------------- //
function DetectedVsFixedChart({ series, grown, reduced }: { series: TrendPoint[]; grown: boolean; reduced: boolean }) {
  if (series.length === 0) {
    return <div style={{ fontSize: 11, color: '#64748b', padding: '24px 0', textAlign: 'center' }}>No trend data yet.</div>;
  }
  const W = 320;
  const H = 132;
  const pad = { l: 24, r: 10, t: 10, b: 22 };
  const innerW = W - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;

  const detected = series.map((p) => p.staleDetected + p.conflictsDetected);
  const fixed = series.map((p) => p.staleFixed + p.conflictsResolved);
  const n = series.length;
  const yMax = Math.max(1, ...detected, ...fixed);

  const xAt = (i: number) => pad.l + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const yAt = (v: number) => pad.t + innerH - (v / yMax) * innerH;
  const toPts = (arr: number[]) => arr.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' ');

  // Backlog area between the two lines.
  const areaPts =
    detected.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' ') +
    ' ' +
    fixed
      .map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`)
      .reverse()
      .join(' ');

  const drawStyle = (delay: string): React.CSSProperties =>
    reduced ? {} : { transition: `stroke-dashoffset 1.1s ease ${delay}` };

  const gridVals = [0, Math.round(yMax / 2), yMax];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Issues detected versus fixed over time">
      {gridVals.map((g) => {
        const gy = yAt(g);
        return (
          <g key={g}>
            <line x1={pad.l} y1={gy} x2={W - pad.r} y2={gy} stroke="rgba(148,163,184,0.12)" strokeWidth={1} />
            <text x={pad.l - 4} y={gy + 3} textAnchor="end" fontSize={7} fill="#475569">
              {g}
            </text>
          </g>
        );
      })}

      <polygon points={areaPts} fill="rgba(245,158,11,0.12)" stroke="none" />

      <polyline
        points={toPts(detected)}
        fill="none"
        stroke={AMBER}
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray="1 1"
        strokeDashoffset={grown ? 0 : 1}
        style={drawStyle('0s')}
      />
      <polyline
        points={toPts(fixed)}
        fill="none"
        stroke={GREEN}
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray="1 1"
        strokeDashoffset={grown ? 0 : 1}
        style={drawStyle('0.15s')}
      />

      {/* end dots */}
      <circle cx={xAt(n - 1)} cy={yAt(detected[n - 1])} r={2.6} fill={AMBER} />
      <circle cx={xAt(n - 1)} cy={yAt(fixed[n - 1])} r={2.6} fill={GREEN} />

      {/* x labels: first + last */}
      <text x={pad.l} y={H - 6} fontSize={7} fill="#475569" textAnchor="start">
        {shortDate(series[0]?.date ?? '')}
      </text>
      <text x={W - pad.r} y={H - 6} fontSize={7} fill="#475569" textAnchor="end">
        {shortDate(series[n - 1]?.date ?? '')}
      </text>
    </svg>
  );
}

// --------------------------------------------------------------------------- //
// Inline SVG: confidence histogram
// --------------------------------------------------------------------------- //
function ConfidenceHistogram({ buckets, grown, reduced }: { buckets: HistogramBucket[]; grown: boolean; reduced: boolean }) {
  if (buckets.length === 0) {
    return <div style={{ fontSize: 11, color: '#64748b', padding: '24px 0', textAlign: 'center' }}>No confidence data yet.</div>;
  }
  const W = 320;
  const H = 132;
  const pad = { l: 24, r: 10, t: 10, b: 24 };
  const innerW = W - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;
  const maxC = Math.max(1, ...buckets.map((b) => b.count));
  const slot = innerW / Math.max(1, buckets.length);
  const barW = slot * 0.6;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="AI confidence distribution">
      <defs>
        <linearGradient id="dgViolet" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#6d28d9" />
        </linearGradient>
      </defs>

      <line x1={pad.l} y1={pad.t + innerH} x2={W - pad.r} y2={pad.t + innerH} stroke="rgba(148,163,184,0.18)" strokeWidth={1} />

      {buckets.map((b, i) => {
        const full = (b.count / maxC) * innerH;
        const h = grown ? full : 0;
        const bx = pad.l + i * slot + (slot - barW) / 2;
        const by = pad.t + innerH - h;
        return (
          <g key={b.bucket}>
            <rect
              x={bx}
              y={by}
              width={barW}
              height={h}
              rx={2}
              fill="url(#dgViolet)"
              style={reduced ? undefined : { transition: 'height 0.6s ease, y 0.6s ease' }}
            />
            <text x={bx + barW / 2} y={by - 3} fontSize={7.5} fill="#94a3b8" textAnchor="middle">
              {grown ? b.count : ''}
            </text>
            <text x={bx + barW / 2} y={H - 8} fontSize={6.5} fill="#475569" textAnchor="middle">
              {b.bucket}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// --------------------------------------------------------------------------- //
// Worst-offender lists (from the corpus report)
// --------------------------------------------------------------------------- //
function DocRefList({
  items,
  color,
  scoreLabel,
  onSelectDoc,
}: {
  items: DocRef[];
  color: string;
  scoreLabel: (score: number) => string;
  onSelectDoc?: (docId: string) => void;
}) {
  if (items.length === 0) {
    return <div style={{ fontSize: 11, color: '#64748b' }}>Nothing flagged.</div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {items.map((d) => (
        <button
          key={d.docId}
          onClick={() => onSelectDoc?.(d.docId)}
          title={d.reasons.join(' · ')}
          style={{
            textAlign: 'left',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 8px',
            borderRadius: 7,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            cursor: onSelectDoc ? 'pointer' : 'default',
            width: '100%',
          }}
        >
          <span
            style={{
              flexShrink: 0,
              minWidth: 38,
              textAlign: 'center',
              padding: '2px 5px',
              borderRadius: 4,
              background: `${color}18`,
              border: `1px solid ${color}33`,
              color,
              fontSize: 11,
              fontWeight: 700,
            }}
          >
            {scoreLabel(d.score)}
          </span>
          <span style={{ flex: 1, minWidth: 0 }}>
            <span
              style={{
                display: 'block',
                fontSize: 12,
                color: '#e2e8f0',
                fontWeight: 500,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {basename(d.docId)}
            </span>
            <span
              style={{
                display: 'block',
                fontSize: 10,
                color: '#64748b',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {d.reasons[0] ?? d.docId}
            </span>
          </span>
        </button>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Main panel
// --------------------------------------------------------------------------- //
export function TrendsPanel({ onSelectDoc }: TrendsPanelProps) {
  const { data: trends, offline: trendsOffline } = useTrends();
  const { data: report, offline: reportOffline } = useAnalysis();
  const reduced = useReducedMotion();
  const offline = trendsOffline || reportOffline;

  // One-shot "grow in" for charts; respects prefers-reduced-motion.
  const [grown, setGrown] = useState(reduced);
  useEffect(() => {
    if (reduced) {
      setGrown(true);
      return;
    }
    const id = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(id);
  }, [reduced]);

  const latestQuality = trends.series.length > 0 ? trends.series[trends.series.length - 1].qualityAvg : report.qualityAvg;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '14px 16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <TrendingUp size={15} color="#a78bfa" />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Corpus Insights</span>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: '#475569' }}>
          as of {trends.asOf.slice(0, 10)}
        </span>
        {offline && (
          <span
            style={{
              padding: '1px 6px',
              borderRadius: 3,
              background: 'rgba(245,158,11,0.1)',
              border: '1px solid rgba(245,158,11,0.2)',
              color: '#fbbf24',
              fontSize: 9,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            demo
          </span>
        )}
      </div>

      {/* KPIs */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        <Kpi
          icon={<CheckCircle2 size={15} color={GREEN} />}
          label="Proposal acceptance"
          value={pct(trends.proposalAcceptanceRate)}
          color={GREEN}
        />
        <Kpi icon={<ShieldCheck size={15} color={BLUE} />} label="Evidence coverage" value={pct(trends.evidenceCoverage)} color={BLUE} />
        <Kpi icon={<Award size={15} color={VIOLET} />} label="Avg doc quality" value={pct(latestQuality)} color={VIOLET} />
        <Kpi icon={<FileText size={15} color={AMBER} />} label="Documents" value={`${report.totalDocs}`} color={AMBER} />
      </div>

      {/* Detected vs fixed */}
      <Card>
        <SectionLabel icon={<TrendingUp size={12} color="#64748b" />}>Issues detected vs fixed</SectionLabel>
        <DetectedVsFixedChart series={trends.series} grown={grown} reduced={reduced} />
        <div style={{ display: 'flex', gap: 14, marginTop: 6 }}>
          <LegendDot color={AMBER} label="Detected" />
          <LegendDot color={GREEN} label="Fixed" />
        </div>
      </Card>

      {/* Confidence histogram */}
      <Card>
        <SectionLabel icon={<BarChart3 size={12} color="#64748b" />}>AI confidence distribution</SectionLabel>
        <ConfidenceHistogram buckets={trends.confidenceHistogram} grown={grown} reduced={reduced} />
      </Card>

      {/* By repository */}
      <div>
        <SectionLabel icon={<GitBranch size={12} color="#64748b" />}>By repository</SectionLabel>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {trends.byRepo.map((r) => (
            <div
              key={r.repo}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '7px 10px',
                borderRadius: 8,
                background: 'rgba(255,255,255,0.025)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <span style={{ flex: '0 0 84px', fontSize: 12, color: '#e2e8f0', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {r.repo}
              </span>
              <span style={{ flex: '0 0 30px', fontSize: 11, color: '#94a3b8', textAlign: 'right' }}>{r.totalDocs}</span>
              <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: grown ? `${Math.max(0, Math.min(1, r.qualityAvg)) * 100}%` : '0%',
                    background: qualityColor(r.qualityAvg),
                    borderRadius: 3,
                    transition: reduced ? undefined : 'width 0.6s ease',
                  }}
                />
              </div>
              <span style={{ flex: '0 0 30px', fontSize: 11, fontWeight: 600, color: qualityColor(r.qualityAvg), textAlign: 'right' }}>
                {pct(r.qualityAvg)}
              </span>
              <span
                style={{ flex: '0 0 22px', fontSize: 11, fontWeight: 600, color: r.brokenLinks > 0 ? RED : '#475569', textAlign: 'right' }}
                title={`${r.brokenLinks} broken links`}
              >
                {r.brokenLinks}
              </span>
              <span
                style={{ flex: '0 0 22px', fontSize: 11, fontWeight: 600, color: r.atRisk > 0 ? AMBER : '#475569', textAlign: 'right' }}
                title={`${r.atRisk} at-risk docs`}
              >
                {r.atRisk}
              </span>
            </div>
          ))}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', fontSize: 9, color: '#475569', paddingRight: 2 }}>
            <span style={{ flex: '0 0 30px', textAlign: 'right' }}>docs</span>
            <span style={{ flex: '0 0 30px', textAlign: 'right' }}>quality</span>
            <span style={{ flex: '0 0 22px', textAlign: 'right', color: RED }}>brk</span>
            <span style={{ flex: '0 0 22px', textAlign: 'right', color: AMBER }}>risk</span>
          </div>
        </div>
      </div>

      {/* Needs attention (corpus report worst offenders) */}
      <div>
        <SectionLabel icon={<AlertTriangle size={12} color="#64748b" />}>Most at-risk</SectionLabel>
        <DocRefList items={report.mostAtRisk} color={RED} scoreLabel={pct} onSelectDoc={onSelectDoc} />
      </div>
      <div>
        <SectionLabel icon={<FileText size={12} color="#64748b" />}>Lowest quality</SectionLabel>
        <DocRefList items={report.worstQuality} color={AMBER} scoreLabel={pct} onSelectDoc={onSelectDoc} />
      </div>
      <div>
        <SectionLabel icon={<GitBranch size={12} color="#64748b" />}>Most central</SectionLabel>
        <DocRefList items={report.topCentral} color={VIOLET} scoreLabel={pct} onSelectDoc={onSelectDoc} />
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#94a3b8' }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}` }} />
      {label}
    </span>
  );
}
