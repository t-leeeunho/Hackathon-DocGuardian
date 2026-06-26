import { useState } from 'react';
import { X, AlertTriangle, ChevronDown, ChevronRight, Wand2, CheckCircle2 } from 'lucide-react';
import MonacoEditor from '@monaco-editor/react';
import { CitationChip } from '../chat/CitationChip';
import type { AgentProposal, Citation, GraphHighlightEvent } from '../../lib/types';

interface ProposalPanelProps {
  proposal: AgentProposal | null;
  loading?: boolean;
  onClose: () => void;
  onHighlight: (event: GraphHighlightEvent) => void;
  onApprove?: () => void;
  onReject?: () => void;
  approved?: boolean;
}

const ACTION_COLORS: Record<string, string> = {
  create: '#22d3a0',
  update: '#3b82f6',
  merge: '#8b5cf6',
  link: '#06b6d4',
  deprecate: '#f97316',
  flag: '#f59e0b',
};

const RISK_CONFIG = {
  low: { color: '#22d3a0', bg: 'rgba(34,211,160,0.1)', label: 'Low risk' },
  medium: { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', label: 'Medium risk' },
  high: { color: '#ef4444', bg: 'rgba(239,68,68,0.1)', label: 'High risk' },
};

export function ProposalPanel({ proposal, loading, onClose, onHighlight, onApprove, onReject, approved }: ProposalPanelProps) {
  const [reasoningOpen, setReasoningOpen] = useState(false);

  if (!proposal && !loading) return null;

  const citationHighlight = (c: Citation) =>
    onHighlight({
      reason: 'proposal-evidence',
      nodeIds: [c.docId],
      intensity: c.relevance,
      ttlMs: 5000,
    });

  return (
    <div
      className="glass-panel-elevated animate-slide-in-right"
      style={{
        width: 480,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid rgba(139,92,246,0.15)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 12px rgba(139,92,246,0.4)',
          }}
        >
          <Wand2 size={14} color="white" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Proposal Review</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>Guardian-reviewed change</div>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b', padding: 4, borderRadius: 4, display: 'flex' }}
        >
          <X size={16} />
        </button>
      </div>

      {loading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center', opacity: 0.6 }}>
            <div style={{
              width: 40, height: 40, borderRadius: '50%',
              border: '3px solid rgba(139,92,246,0.2)', borderTopColor: '#8b5cf6',
              animation: 'spin 1s linear infinite', margin: '0 auto 12px',
            }} />
            <div style={{ fontSize: 12, color: '#94a3b8' }}>Guardian is reviewing…</div>
          </div>
        </div>
      ) : proposal ? (
        <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Action + Risk badges */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{
              padding: '3px 10px',
              borderRadius: 4,
              background: `${ACTION_COLORS[proposal.action] ?? '#64748b'}20`,
              border: `1px solid ${ACTION_COLORS[proposal.action] ?? '#64748b'}40`,
              color: ACTION_COLORS[proposal.action] ?? '#94a3b8',
              fontSize: 12,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}>
              {proposal.action}
            </span>

            <span style={{
              padding: '3px 10px',
              borderRadius: 4,
              background: RISK_CONFIG[proposal.riskLevel].bg,
              border: `1px solid ${RISK_CONFIG[proposal.riskLevel].color}30`,
              color: RISK_CONFIG[proposal.riskLevel].color,
              fontSize: 12,
              fontWeight: 600,
            }}>
              {RISK_CONFIG[proposal.riskLevel].label}
            </span>

            {proposal.targetDocId && (
              <span style={{ fontSize: 11, color: '#64748b' }}>
                → <span style={{ color: '#a78bfa', fontFamily: 'monospace' }}>{proposal.targetDocId}</span>
              </span>
            )}
          </div>

          {/* Confidence bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b', marginBottom: 5 }}>
              <span>Confidence</span>
              <span style={{ color: '#94a3b8' }}>{Math.round(proposal.confidence * 100)}%</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${proposal.confidence * 100}%`,
                borderRadius: 3,
                background: proposal.confidence >= 0.75
                  ? 'linear-gradient(90deg, #22d3a0, #059669)'
                  : proposal.confidence >= 0.5
                    ? 'linear-gradient(90deg, #f59e0b, #d97706)'
                    : 'linear-gradient(90deg, #ef4444, #dc2626)',
                boxShadow: '0 0 8px currentColor',
                transition: 'width 0.6s ease',
              }} />
            </div>
          </div>

          {/* Needs review warning */}
          {(proposal.confidence < 0.5 || proposal.uncertainty) && (
            <div style={{
              padding: '10px 12px',
              background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.25)',
              borderRadius: 8,
              display: 'flex',
              gap: 10,
              alignItems: 'flex-start',
            }}>
              <AlertTriangle size={14} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
              <div style={{ fontSize: 12, color: '#fcd34d', lineHeight: 1.5 }}>
                <strong>Human review required</strong>
                {proposal.uncertainty && <div style={{ color: '#fbbf24', marginTop: 4, fontWeight: 400 }}>{proposal.uncertainty}</div>}
              </div>
            </div>
          )}

          {/* Conflicts with */}
          {proposal.conflictsWith && proposal.conflictsWith.length > 0 && (
            <div>
              <div style={{ fontSize: 10, color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6, fontWeight: 600 }}>
                ⚡ Conflicts With
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {proposal.conflictsWith.map(id => (
                  <span key={id} style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: 'rgba(239,68,68,0.1)',
                    border: '1px solid rgba(239,68,68,0.25)',
                    color: '#fca5a5',
                    fontSize: 11,
                    fontFamily: 'monospace',
                  }}>
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recommendation */}
          {proposal.recommendation && (
            <div style={{
              padding: '10px 12px',
              background: 'rgba(59,130,246,0.06)',
              border: '1px solid rgba(59,130,246,0.15)',
              borderRadius: 8,
              fontSize: 12,
              color: '#93c5fd',
              lineHeight: 1.6,
            }}>
              <div style={{ fontSize: 10, color: '#3b82f6', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 5 }}>
                Recommendation
              </div>
              {proposal.recommendation}
            </div>
          )}

          {/* Guardian Reasoning (collapsible) */}
          {proposal.guardianReasoning && (
            <div style={{
              border: '1px solid rgba(139,92,246,0.15)',
              borderRadius: 8,
              overflow: 'hidden',
            }}>
              <button
                onClick={() => setReasoningOpen(o => !o)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: 'rgba(139,92,246,0.06)',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  color: '#a78bfa',
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                {reasoningOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                Guardian Reasoning
              </button>
              {reasoningOpen && (
                <div style={{ padding: '10px 12px', fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
                  {proposal.guardianReasoning}
                </div>
              )}
            </div>
          )}

          {/* Draft (Monaco) */}
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6, fontWeight: 600 }}>
              Draft
            </div>
            <div style={{ border: '1px solid rgba(139,92,246,0.2)', borderRadius: 8, overflow: 'hidden' }}>
              <MonacoEditor
                height={280}
                language="markdown"
                value={proposal.draft}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  lineNumbers: 'on',
                  wordWrap: 'on',
                  scrollBeyondLastLine: false,
                  fontSize: 12,
                  padding: { top: 10, bottom: 10 },
                }}
              />
            </div>
          </div>

          {/* Citations */}
          {proposal.citations.length > 0 && (
            <div>
              <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                Evidence
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {proposal.citations.map((c, i) => (
                  <CitationChip
                    key={c.chunkId ?? `${c.docId}-${i}`}
                    citation={c}
                    index={i}
                    onClick={citationHighlight}
                    onHover={citationHighlight}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Approve / Reject */}
          {approved ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                padding: '10px 16px',
                borderRadius: 8,
                background: 'rgba(34,211,160,0.12)',
                border: '1px solid rgba(34,211,160,0.35)',
                color: '#22d3a0',
                fontSize: 13,
                fontWeight: 700,
              }}
            >
              <CheckCircle2 size={15} /> Approved — change applied &amp; provenance recorded
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 8, paddingTop: 4 }}>
              <button
                onClick={onApprove}
                disabled={!onApprove}
                title={onApprove ? 'Approve and apply this change' : 'Approval unavailable'}
                style={{
                  flex: 1,
                  padding: '8px 16px',
                  borderRadius: 8,
                  background: onApprove
                    ? 'linear-gradient(135deg, rgba(34,211,160,0.9), rgba(5,150,105,0.9))'
                    : 'rgba(34,211,160,0.08)',
                  border: '1px solid rgba(34,211,160,0.4)',
                  color: onApprove ? 'white' : '#4b5563',
                  fontSize: 13,
                  cursor: onApprove ? 'pointer' : 'not-allowed',
                  fontWeight: 700,
                  boxShadow: onApprove ? '0 0 14px rgba(34,211,160,0.3)' : 'none',
                }}
              >
                ✓ Approve
              </button>
              <button
                onClick={onReject}
                disabled={!onReject}
                title={onReject ? 'Reject this proposal' : 'Reject unavailable'}
                style={{
                  flex: 1,
                  padding: '8px 16px',
                  borderRadius: 8,
                  background: 'rgba(239,68,68,0.1)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  color: onReject ? '#fca5a5' : '#4b5563',
                  fontSize: 13,
                  cursor: onReject ? 'pointer' : 'not-allowed',
                  fontWeight: 600,
                }}
              >
                ✗ Reject
              </button>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
