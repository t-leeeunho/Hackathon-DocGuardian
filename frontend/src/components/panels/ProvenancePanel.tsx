import { useState } from 'react';
import { X, Copy, Check, ChevronDown, ChevronRight, Clock, FileText, Shield } from 'lucide-react';
import type { DocumentResponse } from '../../lib/types';

interface ProvenancePanelProps {
  doc: DocumentResponse | null;
  onClose: () => void;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      title="Copy to clipboard"
      style={{
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        color: copied ? '#22d3a0' : '#64748b',
        padding: '2px 4px',
        borderRadius: 3,
        transition: 'color 0.2s',
        display: 'inline-flex',
        alignItems: 'center',
      }}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
}

export function ProvenancePanel({ doc, onClose }: ProvenancePanelProps) {
  const [expandedChunks, setExpandedChunks] = useState(false);

  if (!doc) return null;

  const shortSha = doc.commitSha.slice(0, 12);
  const formattedDate = doc.commitDate
    ? new Date(doc.commitDate).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Unknown';

  return (
    <div
      className="glass-panel-elevated animate-slide-in-right"
      style={{
        width: 340,
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
            background: 'linear-gradient(135deg, #22d3a0, #059669)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <FileText size={14} color="white" />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {doc.path.split('/').pop()}
          </div>
          <div style={{ fontSize: 10, color: '#64748b' }}>Provenance</div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: '#64748b',
            padding: 4,
            borderRadius: 4,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {/* Doc ID */}
        <Section label="Document ID">
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <code style={{
              background: 'rgba(0,0,0,0.3)',
              borderRadius: 4,
              padding: '3px 7px',
              fontSize: 11,
              color: '#a78bfa',
              fontFamily: 'JetBrains Mono, monospace',
              wordBreak: 'break-all',
            }}>
              {doc.docId}
            </code>
            <CopyButton text={doc.docId} />
          </div>
        </Section>

        {/* Repo + Path */}
        <Section label="Location">
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
            <span style={{ color: '#64748b' }}>Repo: </span>
            <span style={{ color: '#93c5fd' }}>{doc.repo}</span>
          </div>
          <div style={{ fontSize: 11, color: '#64748b', wordBreak: 'break-all', fontFamily: 'monospace' }}>
            {doc.path}
          </div>
        </Section>

        {/* Commit */}
        <Section label="Last Commit">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <code style={{
              background: 'rgba(0,0,0,0.3)',
              borderRadius: 4,
              padding: '3px 7px',
              fontSize: 11,
              color: '#6ee7b7',
              fontFamily: 'JetBrains Mono, monospace',
            }}>
              {shortSha}
            </code>
            <CopyButton text={doc.commitSha} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#64748b' }}>
            <Clock size={11} />
            {formattedDate}
          </div>
        </Section>

        {/* Chunks */}
        <Section label={`Chunks (${doc.chunks.length})`}>
          <button
            onClick={() => setExpandedChunks(e => !e)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(139,92,246,0.08)',
              border: '1px solid rgba(139,92,246,0.15)',
              borderRadius: 6,
              padding: '6px 10px',
              cursor: 'pointer',
              color: '#a78bfa',
              fontSize: 12,
              width: '100%',
            }}
          >
            {expandedChunks ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {expandedChunks ? 'Hide' : 'Show'} {doc.chunks.length} chunk{doc.chunks.length !== 1 ? 's' : ''}
          </button>

          {expandedChunks && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {doc.chunks.map((chunk, i) => (
                <div
                  key={chunk.chunkId}
                  style={{
                    padding: '8px 10px',
                    background: 'rgba(0,0,0,0.2)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: 6,
                    fontSize: 11,
                  }}
                >
                  <div style={{ color: '#64748b', marginBottom: 4, fontFamily: 'monospace' }}>
                    #{i + 1} — lines {chunk.lineRange[0]}–{chunk.lineRange[1]}
                    <span style={{ marginLeft: 8, color: '#4b5563' }}>({chunk.tokenCount} tokens)</span>
                  </div>
                  {chunk.headingPath.length > 0 && (
                    <div style={{ color: '#a78bfa', marginBottom: 4 }}>
                      {chunk.headingPath.join(' › ')}
                    </div>
                  )}
                  <div style={{ color: '#94a3b8', lineHeight: 1.4, maxHeight: 60, overflow: 'hidden' }}>
                    {chunk.text.slice(0, 120)}{chunk.text.length > 120 ? '…' : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Governance placeholders */}
        <Section label="Governance">
          <div
            style={{
              padding: '10px 12px',
              background: 'rgba(139,92,246,0.05)',
              border: '1px solid rgba(139,92,246,0.1)',
              borderRadius: 6,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <Shield size={13} color="#64748b" />
              <span style={{ color: '#64748b' }}>Last verified:</span>
              <span style={{ color: '#475569' }}>— (not implemented)</span>
            </div>
            <button
              disabled
              title="Governance features coming soon"
              style={{
                padding: '5px 12px',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 5,
                color: '#4b5563',
                fontSize: 11,
                cursor: 'not-allowed',
              }}
            >
              Rollback — Governance features coming soon
            </button>
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#475569',
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}
