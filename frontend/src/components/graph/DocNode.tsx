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

const HEALTH_CONFIG = {
  green: {
    color: '#22d3a0',
    glow: '0 0 12px #22d3a0, 0 0 24px rgba(34, 211, 160, 0.5)',
    glowBright: '0 0 20px #22d3a0, 0 0 40px rgba(34, 211, 160, 0.7), 0 0 60px rgba(34, 211, 160, 0.3)',
    animation: 'breatheGreen 3s ease-in-out infinite',
    bg: 'radial-gradient(circle at 35% 35%, #34d399, #059669)',
    ring: 'rgba(34, 211, 160, 0.6)',
  },
  yellow: {
    color: '#f59e0b',
    glow: '0 0 12px #f59e0b, 0 0 24px rgba(245, 158, 11, 0.5)',
    glowBright: '0 0 20px #f59e0b, 0 0 40px rgba(245, 158, 11, 0.7), 0 0 60px rgba(245, 158, 11, 0.3)',
    animation: 'breatheYellow 3s ease-in-out infinite',
    bg: 'radial-gradient(circle at 35% 35%, #fcd34d, #d97706)',
    ring: 'rgba(245, 158, 11, 0.6)',
  },
  red: {
    color: '#ef4444',
    glow: '0 0 12px #ef4444, 0 0 24px rgba(239, 68, 68, 0.5)',
    glowBright: '0 0 20px #ef4444, 0 0 40px rgba(239, 68, 68, 0.7), 0 0 60px rgba(239, 68, 68, 0.3)',
    animation: 'breatheRed 2s ease-in-out infinite',
    bg: 'radial-gradient(circle at 35% 35%, #f87171, #dc2626)',
    ring: 'rgba(239, 68, 68, 0.6)',
  },
  gray: {
    color: '#6b7280',
    glow: 'none',
    glowBright: '0 0 8px rgba(107, 114, 128, 0.4)',
    animation: 'none',
    bg: 'radial-gradient(circle at 35% 35%, #9ca3af, #4b5563)',
    ring: 'rgba(107, 114, 128, 0.4)',
  },
};

// Normalize size 0-1 → 18-40px diameter
function nodeDiameter(size: number): number {
  const clamped = Math.max(0, Math.min(1, size));
  return Math.round(18 + clamped * 22);
}

export const DocNode = memo(function DocNode({ data, selected }: DocNodeProps) {
  const cfg = HEALTH_CONFIG[data.health] || HEALTH_CONFIG.gray;
  const diameter = nodeDiameter(data.size);
  const isHighlighted = data.highlighted || selected;

  const label =
    data.label.length > 20 ? data.label.slice(0, 18) + '…' : data.label;

  const nodeStyle: React.CSSProperties = {
    width: diameter,
    height: diameter,
    borderRadius: '50%',
    background: data.accessible ? cfg.bg : undefined,
    backgroundColor: data.accessible ? undefined : '#1f2937',
    boxShadow: isHighlighted
      ? `0 0 0 3px ${cfg.ring}, ${cfg.glowBright}`
      : cfg.glow,
    animation: data.accessible && !isHighlighted ? cfg.animation : undefined,
    filter: !data.accessible ? 'grayscale(1) opacity(0.4)' : undefined,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
    transform: isHighlighted ? 'scale(1.1)' : undefined,
    border: selected ? `2px solid ${cfg.color}` : '2px solid rgba(255,255,255,0.08)',
  };

  const labelStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: -(diameter < 30 ? 14 : 16),
    left: '50%',
    transform: 'translateX(-50%)',
    fontSize: '9px',
    color: 'rgba(226, 232, 240, 0.7)',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
    textShadow: `0 0 8px ${cfg.color}`,
    fontFamily: 'system-ui, sans-serif',
    letterSpacing: '0.02em',
  };

  return (
    <div style={{ position: 'relative', display: 'inline-flex', flexDirection: 'column', alignItems: 'center' }}>
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: 'transparent', border: 'none', width: 1, height: 1 }}
      />

      <div style={nodeStyle} className={isHighlighted ? 'node-highlighted' : ''}>
        {/* Inner highlight shimmer */}
        {data.accessible && (
          <div
            style={{
              position: 'absolute',
              top: '15%',
              left: '15%',
              width: '30%',
              height: '30%',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.25)',
              pointerEvents: 'none',
            }}
          />
        )}

        {/* Lock icon for inaccessible */}
        {!data.accessible && (
          <Lock
            size={Math.max(10, diameter * 0.35)}
            style={{ color: '#6b7280', opacity: 0.8 }}
          />
        )}
      </div>

      <div style={labelStyle}>{label}</div>

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: 'transparent', border: 'none', width: 1, height: 1 }}
      />
    </div>
  );
});
