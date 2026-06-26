import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  X, FileText, Sparkles, Clock, Copy, Check, ArrowUpRight, ArrowDownLeft,
  Link2, Shield, FolderTree,
} from 'lucide-react';
import { api } from '../../lib/api';
import type { DocumentResponse, DocumentSource, GraphEdge, GraphNode } from '../../lib/types';

type Tab = 'document' | 'original' | 'references' | 'details';

interface DocumentViewerProps {
  doc: DocumentResponse | null;
  edges: GraphEdge[];
  nodes: GraphNode[];
  onClose: () => void;
  onNavigate: (docId: string) => void;
  width?: number;
}

const EDGE_META: Record<string, { label: string; color: string }> = {
  references: { label: 'References', color: '#93c5fd' },
  'duplicate-of': { label: 'Duplicate of', color: '#fcd34d' },
  'conflicts-with': { label: 'Conflicts with', color: '#fca5a5' },
  'deprecated-by': { label: 'Deprecated by', color: '#f0abfc' },
  'related-to': { label: 'Related to', color: '#a78bfa' },
  sibling: { label: 'Sibling', color: '#94a3b8' },
};

function stripFrontMatter(md: string): string {
  return md.replace(/^\s*---\n[\s\S]*?\n---\n?/, '').trimStart();
}
function basename(id: string): string {
  return id.split('/').pop() || id;
}

interface Ref {
  otherId: string;
  label: string;
  type: string;
  direction: 'out' | 'in';
}

export function DocumentViewer({ doc, edges, nodes, onClose, onNavigate, width = 400 }: DocumentViewerProps) {
  const [tab, setTab] = useState<Tab>('document');
  const [source, setSource] = useState<DocumentSource | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Fetch the original + AI rewrite whenever a different document is selected.
  useEffect(() => {
    setTab('document');
    setSource(null);
    if (!doc) return;
    let cancelled = false;
    setLoading(true);
    api
      .getDocumentSource(doc.docId)
      .then((s) => !cancelled && setSource(s))
      .catch(() => !cancelled && setSource(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [doc?.docId]);

  const labelById = useMemo(() => {
    const m = new Map<string, string>();
    for (const n of nodes) m.set(n.id, n.label);
    return m;
  }, [nodes]);

  const references = useMemo<Ref[]>(() => {
    if (!doc) return [];
    const out: Ref[] = [];
    for (const e of edges) {
      if (e.source === doc.docId) {
        out.push({ otherId: e.target, label: labelById.get(e.target) || basename(e.target), type: e.type, direction: 'out' });
      } else if (e.target === doc.docId) {
        out.push({ otherId: e.source, label: labelById.get(e.source) || basename(e.source), type: e.type, direction: 'in' });
      }
    }
    return out;
  }, [doc, edges, labelById]);

  if (!doc) return null;

  const aiRewritten = Boolean(doc.aiRewritten);
  const reconstructed = doc.chunks.map((c) => c.text).join('\n\n');
  const aiDoc = stripFrontMatter((source?.aiContent || '').trim() || reconstructed);
  const original = (source?.originalContent || '').trim();
  const hasOriginal = aiRewritten && original.length > 0;
  const activeBody = tab === 'original' ? stripFrontMatter(original) : aiDoc;

  const copyActive = () => {
    const text = tab === 'references' || tab === 'details' ? doc.docId : activeBody;
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const tabs: { id: Tab; label: string; show: boolean }[] = [
    { id: 'document', label: aiRewritten ? 'AI Document' : 'Document', show: true },
    { id: 'original', label: 'Original', show: hasOriginal },
    { id: 'references', label: references.length ? `References (${references.length})` : 'References', show: true },
    { id: 'details', label: 'Details', show: true },
  ];

  const shortSha = (doc.commitSha || '').slice(0, 12);
  const formattedDate = doc.commitDate
    ? new Date(doc.commitDate).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : 'Unknown';

  return (
    <div
      className="glass-panel-elevated animate-slide-in-right"
      style={{ width, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
    >
      {/* Header */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(139,92,246,0.15)', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: aiRewritten ? 'linear-gradient(135deg, #8b5cf6, #6366f1)' : 'linear-gradient(135deg, #22d3a0, #059669)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          {aiRewritten ? <Sparkles size={14} color="white" /> : <FileText size={14} color="white" />}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {doc.title || basename(doc.path)}
          </div>
          <div style={{ fontSize: 10, color: aiRewritten ? '#a78bfa' : '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
            {aiRewritten ? <><Sparkles size={9} /> AI-rewritten document</> : 'Source document'}
          </div>
        </div>
        <button onClick={copyActive} title="Copy" style={iconBtn}>
          {copied ? <Check size={14} color="#22d3a0" /> : <Copy size={14} />}
        </button>
        <button onClick={onClose} title="Close" style={iconBtn}>
          <X size={16} />
        </button>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 2, padding: '8px 10px 0', borderBottom: '1px solid rgba(139,92,246,0.12)', flexShrink: 0 }}>
        {tabs.filter((t) => t.show).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: '7px 11px', fontSize: 11.5, fontWeight: 600, cursor: 'pointer', border: 'none',
              borderBottom: `2px solid ${tab === t.id ? '#8b5cf6' : 'transparent'}`,
              background: 'transparent', color: tab === t.id ? '#c4b5fd' : '#64748b',
              transition: 'color 0.15s, border-color 0.15s',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {loading && !source && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#64748b', fontSize: 12 }}>
            <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(139,92,246,0.2)', borderTopColor: '#8b5cf6', animation: 'spin 1s linear infinite' }} />
            Loading document…
          </div>
        )}

        {/* AI document / source */}
        {tab === 'document' && (
          <>
            {aiRewritten && (
              <div style={banner}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#c4b5fd', marginBottom: doc.rationale || doc.originalPath ? 6 : 0 }}>
                  <Sparkles size={12} /> Rewritten by the Librarian for AI agents
                </div>
                {doc.originalPath && doc.originalPath !== doc.path && (
                  <div style={{ fontSize: 10.5, color: '#64748b', display: 'flex', alignItems: 'center', gap: 5, marginBottom: doc.rationale ? 5 : 0 }}>
                    <FolderTree size={11} />
                    <code style={{ color: '#fca5a5', fontFamily: 'monospace' }}>{doc.originalPath}</code>
                    <span>→</span>
                    <code style={{ color: '#6ee7b7', fontFamily: 'monospace' }}>{doc.path}</code>
                  </div>
                )}
                {doc.rationale && <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>{doc.rationale}</div>}
              </div>
            )}
            <div className="prose-cosmic doc-md">
              <ReactMarkdown>{aiDoc || '_(empty document)_'}</ReactMarkdown>
            </div>
          </>
        )}

        {/* Original drop-off */}
        {tab === 'original' && (
          <>
            <div style={{ ...banner, borderColor: 'rgba(148,163,184,0.2)', background: 'rgba(148,163,184,0.06)' }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>
                The user's untouched original{doc.originalPath ? <> — dropped at <code style={{ color: '#fca5a5', fontFamily: 'monospace' }}>{doc.originalPath}</code></> : ''}.
              </div>
            </div>
            <div className="prose-cosmic doc-md">
              <ReactMarkdown>{activeBody || '_(no original stored)_'}</ReactMarkdown>
            </div>
          </>
        )}

        {/* References / related documents */}
        {tab === 'references' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {references.length === 0 && (
              <div style={{ fontSize: 12, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Link2 size={13} /> No references or related documents.
              </div>
            )}
            {references.map((r, i) => {
              const meta = EDGE_META[r.type] || { label: r.type, color: '#94a3b8' };
              return (
                <button
                  key={`${r.otherId}-${r.type}-${i}`}
                  onClick={() => onNavigate(r.otherId)}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 6, cursor: 'pointer', textAlign: 'left', width: '100%' }}
                >
                  {r.direction === 'out' ? <ArrowUpRight size={13} color="#64748b" /> : <ArrowDownLeft size={13} color="#64748b" />}
                  <span style={{ fontSize: 10, fontWeight: 600, color: meta.color, padding: '2px 6px', borderRadius: 4, background: `${meta.color}1a`, whiteSpace: 'nowrap' }}>
                    {meta.label}
                  </span>
                  <span style={{ fontSize: 12, color: '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.label}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Provenance / details */}
        {tab === 'details' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Detail label="Document ID">
              <code style={codeBox}>{doc.docId}</code>
            </Detail>
            <Detail label="Location">
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                <span style={{ color: '#64748b' }}>Repo: </span>
                <span style={{ color: '#93c5fd' }}>{doc.repo}</span>
              </div>
              <div style={{ fontSize: 11, color: '#64748b', wordBreak: 'break-all', fontFamily: 'monospace', marginTop: 4 }}>{doc.path}</div>
              {doc.originalPath && (
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                  <span style={{ color: '#475569' }}>Originally: </span>
                  <code style={{ color: '#fca5a5', fontFamily: 'monospace' }}>{doc.originalPath}</code>
                </div>
              )}
            </Detail>
            <Detail label="Last Commit">
              {shortSha ? (
                <>
                  <code style={{ ...codeBox, color: '#6ee7b7' }}>{shortSha}</code>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#64748b', marginTop: 6 }}>
                    <Clock size={11} /> {formattedDate}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 11, color: '#475569' }}>No source commit (user drop-off).</div>
              )}
            </Detail>
            <Detail label={`Chunks (${doc.chunks.length})`}>
              <div style={{ fontSize: 11, color: '#64748b' }}>{doc.chunks.length} embedded chunk{doc.chunks.length !== 1 ? 's' : ''} indexed for retrieval.</div>
            </Detail>
            <Detail label="Governance">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#64748b' }}>
                <Shield size={13} /> Approval &amp; rollback via the proposal flow.
              </div>
            </Detail>
          </div>
        )}
      </div>
    </div>
  );
}

const iconBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b',
  padding: 4, borderRadius: 4, display: 'flex', alignItems: 'center',
};

const banner: React.CSSProperties = {
  padding: '10px 12px', marginBottom: 14, background: 'rgba(139,92,246,0.06)',
  border: '1px solid rgba(139,92,246,0.18)', borderRadius: 6,
};

const codeBox: React.CSSProperties = {
  background: 'rgba(0,0,0,0.3)', borderRadius: 4, padding: '3px 7px', fontSize: 11,
  color: '#a78bfa', fontFamily: 'JetBrains Mono, monospace', wordBreak: 'break-all',
};

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#475569', marginBottom: 8 }}>
        {label}
      </div>
      {children}
    </div>
  );
}
