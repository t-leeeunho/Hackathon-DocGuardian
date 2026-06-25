import { useState, useEffect, useMemo } from 'react';
import { ChevronRight, ChevronDown, File, Folder, FolderOpen, Search, Sparkles } from 'lucide-react';
import { api } from '../../lib/api';
import { fixtureTree } from '../../lib/fixtures';
import type { TreeNode } from '../../lib/types';

interface FileTreeProps {
  onFileSelect?: (path: string) => void;
  selectedPath?: string;
  /** Doc IDs cited by the latest chat answer — highlighted + auto-revealed. */
  highlightedPaths?: string[];
}

interface TreeNodeItemProps {
  node: TreeNode;
  depth: number;
  selectedPath?: string;
  onSelect: (path: string) => void;
  filter: string;
  highlighted: Set<string>;
}

function matchesFilter(node: TreeNode, filter: string): boolean {
  if (!filter) return true;
  const lower = filter.toLowerCase();
  if (node.name.toLowerCase().includes(lower)) return true;
  if (node.children) return node.children.some(c => matchesFilter(c, filter));
  return false;
}

function nodeContainsHighlight(node: TreeNode, set: Set<string>): boolean {
  if (set.size === 0) return false;
  if (node.type !== 'directory') return set.has(node.path);
  return (node.children ?? []).some(c => nodeContainsHighlight(c, set));
}

function TreeNodeItem({ node, depth, selectedPath, onSelect, filter, highlighted }: TreeNodeItemProps) {
  const [expanded, setExpanded] = useState(depth < 1);
  const containsCited = useMemo(() => nodeContainsHighlight(node, highlighted), [node, highlighted]);

  // Auto-reveal folders that contain a cited document when a chat answer arrives.
  useEffect(() => {
    if (containsCited && node.type === 'directory') setExpanded(true);
  }, [containsCited, node.type]);

  if (!matchesFilter(node, filter)) return null;

  const isDir = node.type === 'directory';
  const isSelected = selectedPath === node.path;
  const isCited = !isDir && highlighted.has(node.path);
  const indent = depth * 14;
  // Documents rewritten by the AI live under the `curated/` namespace.
  const isAi = node.path === 'curated' || node.path.startsWith('curated/');

  if (isDir) {
    return (
      <div>
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            width: '100%',
            padding: `5px 10px 5px ${10 + indent}px`,
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: '#94a3b8',
            fontSize: 12,
            textAlign: 'left',
            borderRadius: 4,
            transition: 'background 0.15s',
          }}
          onMouseOver={e => (e.currentTarget.style.background = 'rgba(139,92,246,0.08)')}
          onMouseOut={e => (e.currentTarget.style.background = 'transparent')}
        >
          <span style={{ color: '#4b5563', flexShrink: 0 }}>
            {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          </span>
          {expanded ? (
            <FolderOpen size={13} color={isAi ? '#c084fc' : '#8b5cf6'} style={{ flexShrink: 0 }} />
          ) : (
            <Folder size={13} color={isAi ? '#c084fc' : '#6366f1'} style={{ flexShrink: 0 }} />
          )}
          <span style={{ fontWeight: 600, letterSpacing: '0.01em', color: isAi ? '#d8b4fe' : '#c4b5fd' }}>
            {node.path === 'curated' ? 'AI Curated' : node.name}
          </span>
          {node.path === 'curated' && (
            <Sparkles size={11} color="#c084fc" style={{ flexShrink: 0, marginLeft: 2 }} />
          )}
          {containsCited && !expanded && (
            <span
              title="Contains a referenced document"
              style={{ marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%', background: '#f59e0b', boxShadow: '0 0 6px rgba(245,158,11,0.8)', flexShrink: 0 }}
            />
          )}
        </button>

        {expanded && node.children && (
          <div>
            {node.children.map(child => (
              <TreeNodeItem
                key={child.path}
                node={child}
                depth={depth + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
                filter={filter}
                highlighted={highlighted}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      onClick={() => onSelect(node.path)}
      title={node.summary ? `${node.name} — ${node.summary}` : node.name}
      className={isCited && !isSelected ? 'tree-cited' : undefined}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        width: '100%',
        padding: `4px 10px 4px ${10 + indent}px`,
        background: isSelected ? 'rgba(139,92,246,0.15)' : isCited ? 'rgba(245,158,11,0.13)' : 'transparent',
        border: isSelected
          ? '1px solid rgba(139,92,246,0.3)'
          : isCited
            ? '1px solid rgba(245,158,11,0.4)'
            : '1px solid transparent',
        cursor: 'pointer',
        color: isSelected ? '#c4b5fd' : isCited ? '#fcd34d' : '#94a3b8',
        fontSize: 12,
        textAlign: 'left',
        borderRadius: 4,
        transition: 'all 0.15s',
        marginRight: 8,
        boxShadow: isSelected
          ? '0 0 8px rgba(139,92,246,0.2)'
          : isCited
            ? '0 0 10px rgba(245,158,11,0.25)'
            : 'none',
      }}
      onMouseOver={e => {
        if (!isSelected && !isCited) {
          (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.08)';
          (e.currentTarget as HTMLElement).style.color = '#c4b5fd';
        }
      }}
      onMouseOut={e => {
        if (!isSelected && !isCited) {
          (e.currentTarget as HTMLElement).style.background = 'transparent';
          (e.currentTarget as HTMLElement).style.color = '#94a3b8';
        }
      }}
    >
      {isAi ? (
        <Sparkles size={12} color={isSelected ? '#d8b4fe' : '#c084fc'} style={{ flexShrink: 0 }} />
      ) : (
        <File size={12} color={isSelected ? '#a78bfa' : isCited ? '#f59e0b' : '#475569'} style={{ flexShrink: 0 }} />
      )}
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {node.name}
      </span>
      {isCited && (
        <span style={{
          marginLeft: isAi ? 4 : 'auto', flexShrink: 0, fontSize: 8, fontWeight: 700,
          color: '#fbbf24', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)',
          borderRadius: 3, padding: '0 4px', letterSpacing: '0.05em',
        }}>REF</span>
      )}
      {isAi && (
        <span style={{
          marginLeft: isCited ? 4 : 'auto', fontSize: 8, fontWeight: 700, color: '#c084fc',
          background: 'rgba(192,132,252,0.12)', border: '1px solid rgba(192,132,252,0.3)',
          borderRadius: 3, padding: '0 4px', letterSpacing: '0.05em', flexShrink: 0,
        }}>AI</span>
      )}
    </button>
  );
}

export function FileTree({ onFileSelect, selectedPath, highlightedPaths }: FileTreeProps) {
  const [nodes, setNodes] = useState<TreeNode[]>([]);
  const [filter, setFilter] = useState('');
  const [offline, setOffline] = useState(false);
  const highlighted = useMemo(() => new Set(highlightedPaths ?? []), [highlightedPaths]);

  useEffect(() => {
    api.getTree()
      .then(setNodes)
      .catch(() => {
        setNodes(fixtureTree);
        setOffline(true);
      });
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{ padding: '12px 10px 8px', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <Folder size={13} color="#8b5cf6" />
          <span style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Sources
          </span>
          {offline && (
            <span style={{
              marginLeft: 'auto',
              padding: '1px 5px',
              borderRadius: 3,
              background: 'rgba(245,158,11,0.1)',
              border: '1px solid rgba(245,158,11,0.2)',
              color: '#fbbf24',
              fontSize: 9,
              fontWeight: 700,
            }}>
              OFFLINE
            </span>
          )}
        </div>

        {/* Search */}
        <div style={{ position: 'relative' }}>
          <Search
            size={12}
            style={{
              position: 'absolute',
              left: 8,
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#4b5563',
              pointerEvents: 'none',
            }}
          />
          <input
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="Filter files…"
            style={{
              width: '100%',
              padding: '5px 8px 5px 26px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(139,92,246,0.15)',
              borderRadius: 5,
              color: '#e2e8f0',
              fontSize: 12,
              outline: 'none',
              fontFamily: 'system-ui, sans-serif',
            }}
          />
        </div>
      </div>

      {/* Tree */}
      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 16 }}>
        {nodes.length === 0 ? (
          <div style={{ padding: '20px 16px', textAlign: 'center', color: '#4b5563', fontSize: 12 }}>
            Loading sources…
          </div>
        ) : (
          nodes.map(node => (
            <TreeNodeItem
              key={node.path}
              node={node}
              depth={0}
              selectedPath={selectedPath}
              onSelect={path => onFileSelect?.(path)}
              filter={filter}
              highlighted={highlighted}
            />
          ))
        )}
      </div>
    </div>
  );
}
