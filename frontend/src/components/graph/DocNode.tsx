import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Lock } from 'lucide-react';
import type { GraphNode } from '../../lib/types';

interface DocNodeData extends GraphNode {
  highlighted?: boolean;
  selected?: boolean;
}

interface DocNodeProps {
  data: DocNodeData;
  selected: boolean;
}

// 4-pointed sparkle star (✦)
const STAR_CLIP =
  'polygon(50% 2%, 53% 47%, 98% 50%, 53% 53%, 50% 98%, 47% 53%, 2% 50%, 47% 47%)';

const HEALTH_CONFIG = {
  green:  { color: '#22d3a0', shadow: 'drop-shadow(0 0 5px #22d3a0) drop-shadow(0 0 12px rgba(34,211,160,0.6))', shadowBright: 'drop-shadow(0 0 8px #22d3a0) drop-shadow(0 0 20px #22d3a0)',  animation: 'breatheGreen 3s ease-in-out infinite', bg: 'linear-gradient(135deg, #34d399, #059669)' },
  yellow: { color: '#f59e0b', shadow: 'drop-shadow(0 0 5px #f59e0b) drop-shadow(0 0 12px rgba(245,158,11,0.6))', shadowBright: 'drop-shadow(0 0 8px #f59e0b) drop-shadow(0 0 20px #f59e0b)', animation: 'breatheYellow 3s ease-in-out infinite', bg: 'linear-gradient(135deg, #fcd34d, #d97706)' },
  red:    { color: '#ef4444', shadow: 'drop-shadow(0 0 5px #ef4444) drop-shadow(0 0 12px rgba(239,68,68,0.6))',   shadowBright: 'drop-shadow(0 0 8px #ef4444) drop-shadow(0 0 20px #ef4444)',   animation: 'breatheRed 2s ease-in-out infinite',   bg: 'linear-gradient(135deg, #f87171, #dc2626)' },
  gray:   { color: '#6b7280', shadow: 'drop-shadow(0 0 3px rgba(107,114,128,0.4))',                               shadowBright: 'drop-shadow(0 0 6px rgba(107,114,128,0.7))',                  animation: 'none',                                  bg: 'linear-gradient(135deg, #9ca3af, #4b5563)' },
};

// Normalize size 0-1 → 16-32px
function nodeSize(size: number): number {
  const clamped = Math.max(0, Math.min(1, size));
  return Math.round(16 + clamped * 16);
}

export const DocNode = memo(function DocNode({ data, selected }: DocNodeProps) {
  const cfg = HEALTH_CONFIG[data.health] || HEALTH_CONFIG.gray;
  const sz = nodeSize(data.size);
  const isHighlighted = data.highlighted || selected;

  const label = data.label.length > 18 ? data.label.slice(0, 16) + '…' : data.label;

  const nodeStyle: React.CSSProperties = {
    width: sz,
    height: sz,
    clipPath: STAR_CLIP,
    background: data.accessible ? cfg.bg : '#374151',
    filter: !data.accessible
      ? 'grayscale(1) opacity(0.35)'
      : isHighlighted
        ? cfg.shadowBright
        : cfg.shadow,
    animation: data.accessible && !isHighlighted ? cfg.animation : undefined,
    cursor: 'pointer',
    transition: 'transform 0.15s ease, filter 0.15s ease',
    transform: isHighlighted ? 'scale(1.35) rotate(15deg)' : 'rotate(0deg)',
    flexShrink: 0,
  };

  const labelStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: -13,
    left: '50%',
    transform: 'translateX(-50%)',
    fontSize: '8px',
    color: 'rgba(203, 213, 225, 0.75)',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
    textShadow: `0 0 6px ${cfg.color}`,
    fontFamily: 'system-ui, sans-serif',
    letterSpacing: '0.02em',
  };

  return (
    <div style={{ position: 'relative', display: 'inline-flex', flexDirection: 'column', alignItems: 'center' }}>
      <Handle type="target" position={Position.Top}    style={{ background: 'transparent', border: 'none', width: 1, height: 1 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: 'transparent', border: 'none', width: 1, height: 1 }} />
      <Handle type="target" position={Position.Left}   style={{ background: 'transparent', border: 'none', width: 1, height: 1 }} />
      <Handle type="source" position={Position.Right}  style={{ background: 'transparent', border: 'none', width: 1, height: 1 }} />

      <div style={nodeStyle} className={isHighlighted ? 'node-highlighted' : ''}>
        {!data.accessible && (
          <Lock size={Math.max(6, sz * 0.4)} style={{ color: '#9ca3af', opacity: 0.8, position: 'absolute' }} />
        )}
      </div>

      <div style={labelStyle}>{label}</div>
    </div>
  );
});

