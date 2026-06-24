import type { Citation } from '../../lib/types';

interface CitationChipProps {
  citation: Citation;
  index: number;
  onClick?: (citation: Citation) => void;
  onHover?: (citation: Citation) => void;
}

export function CitationChip({ citation, index, onClick, onHover }: CitationChipProps) {
  const label = citation.docId.replace('doc-', '');
  const shortSha = citation.commitSha.slice(0, 7);
  const lineInfo = citation.lineRange ? `:${citation.lineRange[0]}-${citation.lineRange[1]}` : '';
  const relevancePct = Math.round(citation.relevance * 100);

  const relevanceColor =
    citation.relevance >= 0.8
      ? '#22d3a0'
      : citation.relevance >= 0.6
        ? '#f59e0b'
        : '#ef4444';

  return (
    <button
      onClick={() => onClick?.(citation)}
      onMouseEnter={() => onHover?.(citation)}
      title={citation.text ?? `${citation.docId}${lineInfo}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '3px 8px',
        borderRadius: 4,
        background: 'rgba(139,92,246,0.12)',
        border: '1px solid rgba(139,92,246,0.25)',
        color: '#a78bfa',
        fontSize: 11,
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
        cursor: 'pointer',
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
        maxWidth: 240,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}
      onMouseOver={e => {
        (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.22)';
        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(139,92,246,0.5)';
      }}
      onMouseOut={e => {
        (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.12)';
        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(139,92,246,0.25)';
      }}
    >
      <span style={{ color: '#818cf8', marginRight: 2 }}>[{index + 1}]</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {label}{lineInfo}
      </span>
      <span style={{ color: '#64748b', margin: '0 2px' }}>@</span>
      <span style={{ color: '#64748b' }}>{shortSha}</span>
      <span
        style={{
          marginLeft: 4,
          padding: '1px 4px',
          borderRadius: 3,
          background: `rgba(${relevancePct >= 80 ? '34,211,160' : relevancePct >= 60 ? '245,158,11' : '239,68,68'},0.15)`,
          color: relevanceColor,
          fontSize: 10,
          fontWeight: 600,
        }}
      >
        {relevancePct}%
      </span>
    </button>
  );
}
