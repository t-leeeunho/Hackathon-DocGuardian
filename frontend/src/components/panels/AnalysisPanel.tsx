import {
  FileText,
  AlertTriangle,
  Unlink,
  Unplug,
  Sparkles,
  Clock,
  GitBranch,
  Loader2,
} from 'lucide-react';
import { useDocAnalysis } from '../../hooks/useAnalysis';
import type { DocAnalysis, GraphNode, LlmQualityNotes } from '../../lib/types';

interface AnalysisPanelProps {
  docId: string;
  /** Graph node (overlay fields) used as a lightweight fallback when no per-doc
   *  analysis fixture exists for the selected doc in demo mode. */
  node?: GraphNode | null;
}

// Score → palette (project accent colors).
const GREEN = '#22d3a0';
const AMBER = '#f59e0b';
const VIOLET = '#8b5cf6';
const BLUE = '#3b82f6';
const RED = '#ef4444';

function qualityColor(score: number): string {
  return score >= 0.75 ? GREEN : score >= 0.5 ? AMBER : RED;
}
function riskColor(score: number): string {
  return score >= 0.66 ? RED : score >= 0.33 ? AMBER : GREEN;
}
function basename(id: string): string {
  return id.split('/').pop() || id;
}
function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

// --------------------------------------------------------------------------- //
// Small inline building blocks (match the app's inline-style convention)
// --------------------------------------------------------------------------- //
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 10,
        color: '#64748b',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        fontWeight: 600,
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  );
}

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ color, fontWeight: 600 }}>{pct(clamped)}</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${clamped * 100}%`,
            borderRadius: 3,
            background: color,
            boxShadow: `0 0 8px ${color}80`,
            transition: 'width 0.6s ease',
          }}
        />
      </div>
    </div>
  );
}

function StatChip({ label, value, color }: { label: string; value: React.ReactNode; color: string }) {
  return (
    <div
      style={{
        flex: '1 1 auto',
        minWidth: 78,
        padding: '7px 10px',
        borderRadius: 8,
        background: `${color}10`,
        border: `1px solid ${color}22`,
      }}
    >
      <div style={{ fontSize: 15, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 10, color: '#64748b', marginTop: 3 }}>{label}</div>
    </div>
  );
}

function Badge({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 4,
        background: `${color}18`,
        border: `1px solid ${color}33`,
        color,
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {children}
    </span>
  );
}

function ReasonList({ reasons, color }: { reasons: string[]; color: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {reasons.map((r, i) => (
        <div key={i} style={{ display: 'flex', gap: 7, alignItems: 'flex-start', fontSize: 12, color: '#cbd5e1', lineHeight: 1.45 }}>
          <AlertTriangle size={12} color={color} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{r}</span>
        </div>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// LLM notes card (opt-in)
// --------------------------------------------------------------------------- //
function LlmNotesCard({ notes }: { notes: LlmQualityNotes }) {
  return (
    <div
      style={{
        border: `1px solid ${VIOLET}33`,
        borderRadius: 10,
        background: `${VIOLET}0d`,
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Sparkles size={13} color="#a78bfa" />
        <span style={{ fontSize: 11, color: '#a78bfa', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          AI Quality Notes
        </span>
        {notes.clarityScore != null && (
          <span style={{ marginLeft: 'auto' }}>
            <Badge color={qualityColor(notes.clarityScore)}>Clarity {pct(notes.clarityScore)}</Badge>
          </span>
        )}
      </div>

      {notes.issues.length > 0 && (
        <div>
          <SectionLabel>Issues</SectionLabel>
          <ReasonList reasons={notes.issues} color={AMBER} />
        </div>
      )}

      {notes.suggestedSections.length > 0 && (
        <div>
          <SectionLabel>Suggested sections</SectionLabel>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {notes.suggestedSections.map((s) => (
              <span
                key={s}
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: 'rgba(139,92,246,0.12)',
                  border: '1px solid rgba(139,92,246,0.28)',
                  color: '#c4b5fd',
                  fontSize: 11,
                }}
              >
                + {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {notes.issues.length === 0 && notes.suggestedSections.length === 0 && (
        <div style={{ fontSize: 12, color: '#94a3b8' }}>No structural gaps flagged.</div>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Main panel
// --------------------------------------------------------------------------- //
export function AnalysisPanel({ docId, node }: AnalysisPanelProps) {
  const { data, loading, offline, error, llmLoading, llmRequested, explainWithAi } = useDocAnalysis(docId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '14px 16px' }}>
      {/* Doc header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <FileText size={15} color="#a78bfa" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {basename(docId)}
          </div>
          <div style={{ fontSize: 10, color: '#64748b', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {docId}
          </div>
        </div>
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

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#94a3b8', fontSize: 12, padding: '20px 0', justifyContent: 'center' }}>
          <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
          Analyzing document…
        </div>
      ) : data ? (
        <FullBreakdown
          data={data}
          llmLoading={llmLoading}
          llmRequested={llmRequested}
          onExplain={explainWithAi}
        />
      ) : (
        <FallbackBreakdown node={node ?? null} error={error} />
      )}
    </div>
  );
}

function FullBreakdown({
  data,
  llmLoading,
  llmRequested,
  onExplain,
}: {
  data: DocAnalysis;
  llmLoading: boolean;
  llmRequested: boolean;
  onExplain: () => void;
}) {
  const { quality, links, drift, centrality, llm } = data;

  return (
    <>
      {/* Quality */}
      <div>
        <SectionLabel>Quality</SectionLabel>
        <Bar label="Overall quality" value={quality.qualityScore} color={qualityColor(quality.qualityScore)} />
        <Bar label="Completeness" value={quality.completenessScore} color={BLUE} />
        <Bar label="Structure" value={quality.structureScore} color={VIOLET} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
          <StatChip label="Reading ease" value={Math.round(quality.readability)} color={GREEN} />
          <StatChip label="Grade level" value={quality.gradeLevel.toFixed(1)} color={BLUE} />
          <StatChip label="Words" value={quality.wordCount} color={VIOLET} />
          <StatChip
            label="Placeholders"
            value={quality.placeholderCount}
            color={quality.placeholderCount > 0 ? AMBER : '#64748b'}
          />
        </div>
        {quality.issues.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <ReasonList reasons={quality.issues} color={AMBER} />
          </div>
        )}
      </div>

      {/* Links */}
      <div>
        <SectionLabel>Links &amp; structure</SectionLabel>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: links.brokenInternal.length > 0 ? 10 : 0 }}>
          <Badge color={links.brokenLinkCount > 0 ? RED : '#64748b'}>
            <Unlink size={11} /> {links.brokenLinkCount} broken
          </Badge>
          <Badge color={BLUE}>{links.externalCount} external</Badge>
          {links.orphan && (
            <Badge color={AMBER}>
              <Unplug size={11} /> orphan
            </Badge>
          )}
          {links.deadEnd && <Badge color="#94a3b8">dead-end</Badge>}
        </div>
        {links.brokenInternal.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {links.brokenInternal.map((t) => (
              <div
                key={t}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 7,
                  fontSize: 11,
                  fontFamily: 'monospace',
                  color: '#fca5a5',
                  padding: '4px 8px',
                  borderRadius: 6,
                  background: 'rgba(239,68,68,0.07)',
                  border: '1px solid rgba(239,68,68,0.18)',
                }}
              >
                <Unlink size={11} color={RED} style={{ flexShrink: 0 }} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Drift / risk */}
      <div>
        <SectionLabel>Drift &amp; risk</SectionLabel>
        <Bar label="At-risk score" value={drift.riskScore} color={riskColor(drift.riskScore)} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '10px 0' }}>
          <Badge color={BLUE}>
            <Clock size={11} /> {drift.ageDays}d old
          </Badge>
          {drift.isStale ? <Badge color={RED}>stale</Badge> : <Badge color={GREEN}>fresh</Badge>}
          <Badge color={VIOLET}>
            <GitBranch size={11} /> centrality {pct(centrality)}
          </Badge>
        </div>
        {drift.riskReasons.length > 0 && <ReasonList reasons={drift.riskReasons} color={riskColor(drift.riskScore)} />}
      </div>

      {/* LLM enhancement */}
      <div>
        <SectionLabel>AI enhancement</SectionLabel>
        {llm ? (
          <LlmNotesCard notes={llm} />
        ) : (
          <>
            <button
              onClick={onExplain}
              disabled={llmLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 7,
                padding: '7px 12px',
                borderRadius: 8,
                background: 'linear-gradient(135deg, rgba(139,92,246,0.22), rgba(59,130,246,0.16))',
                border: '1px solid rgba(139,92,246,0.35)',
                cursor: llmLoading ? 'wait' : 'pointer',
                color: '#c4b5fd',
                fontSize: 12,
                fontWeight: 600,
                opacity: llmLoading ? 0.7 : 1,
              }}
            >
              {llmLoading ? (
                <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
              ) : (
                <Sparkles size={13} />
              )}
              {llmLoading ? 'Asking the Librarian…' : 'Explain with AI'}
            </button>
            {llmRequested && !llmLoading && (
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 8, lineHeight: 1.5 }}>
                No AI notes returned — semantic enhancement needs a live backend with Azure OpenAI
                configured. The deterministic analysis above still applies.
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}

/** Shown when there's no per-doc analysis fixture (demo) for the selected doc. */
function FallbackBreakdown({ node, error }: { node: GraphNode | null; error: string | null }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {node && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {node.qualityScore != null && (
            <StatChip label="Quality" value={pct(node.qualityScore)} color={qualityColor(node.qualityScore)} />
          )}
          {node.centrality != null && <StatChip label="Centrality" value={pct(node.centrality)} color={VIOLET} />}
          {node.brokenLinkCount != null && (
            <StatChip
              label="Broken links"
              value={node.brokenLinkCount}
              color={node.brokenLinkCount > 0 ? RED : '#64748b'}
            />
          )}
          {node.orphan && <StatChip label="Status" value="orphan" color={AMBER} />}
        </div>
      )}
      <div
        style={{
          fontSize: 12,
          color: '#94a3b8',
          lineHeight: 1.5,
          padding: '10px 12px',
          borderRadius: 8,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {error ?? 'Detailed analysis for this document is available with a live backend.'}
      </div>
    </div>
  );
}
