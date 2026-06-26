import type { Citation } from '../../lib/types';
import { FileText, GitCommit } from 'lucide-react';

interface ReferenceCardProps {
  citation: Citation;
  index: number;
  onClick?: (citation: Citation) => void;
  onHover?: (citation: Citation) => void;
}

/** A detailed evidence reference: doc, location, commit, relevance, and a snippet. */
export function ReferenceCard({ citation, index, onClick, onHover }: ReferenceCardProps) {
  const name = citation.docId.split('/').pop() || citation.docId;
  const dir = citation.docId.includes('/')
    ? citation.docId.slice(0, citation.docId.lastIndexOf('/'))
    : '';
  const shortSha = (citation.commitSha || '').slice(0, 7);
  const lines = citation.lineRange ? `L${citation.lineRange[0]}–${citation.lineRange[1]}` : '';
  const pct = Math.round((citation.relevance ?? 0) * 100);
  const color = citation.relevance >= 0.8 ? '#22d3a0' : citation.relevance >= 0.6 ? '#f59e0b' : '#ef4444';

  return (
    <button
      onClick={() => onClick?.(citation)}
      onMouseEnter={() => onHover?.(citation)}
      title={`Open ${citation.docId}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
        width: '100%',
        textAlign: 'left',
        padding: '8px 10px',
        borderRadius: 8,
        background: 'rgba(139,92,246,0.07)',
        border: '1px solid rgba(139,92,246,0.2)',
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
      onMouseOver={(e) => {
        (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.14)';
        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(139,92,246,0.45)';
      }}
      onMouseOut={(e) => {
        (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.07)';
        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(139,92,246,0.2)';
      }}
    >
      {/* Title row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%' }}>
        <span style={{ color: '#818cf8', fontSize: 11, fontWeight: 700, fontFamily: 'monospace', flexShrink: 0 }}>
          [{index + 1}]
        </span>
        <FileText size={12} color="#a78bfa" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {name}
        </span>
        <span
          style={{
            marginLeft: 'auto', flexShrink: 0,
            padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 700,
            background: `${color}1f`, color,
          }}
        >
          {pct}%
        </span>
      </div>

      {/* Location row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, color: '#64748b', fontFamily: 'monospace' }}>
        {dir && (
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, minWidth: 0 }}>
            {dir}
          </span>
        )}
        {lines && <span style={{ flexShrink: 0, color: '#93c5fd' }}>{lines}</span>}
        {shortSha && (
          <span style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 3, color: '#6ee7b7' }}>
            <GitCommit size={9} /> {shortSha}
          </span>
        )}
      </div>

      {/* Snippet */}
      {citation.text && (
        <div
          style={{
            fontSize: 11,
            color: '#94a3b8',
            lineHeight: 1.45,
            borderLeft: '2px solid rgba(139,92,246,0.35)',
            paddingLeft: 8,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {citation.text}
        </div>
      )}
    </button>
  );
}
