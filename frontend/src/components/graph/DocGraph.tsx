import { useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  type Node,
  type Edge,
  type OnConnect,
  type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { DocNode } from './DocNode';
import { SparkleBackground } from './SparkleBackground';
import type { GraphDTO, GraphNode as GNode } from '../../lib/types';
import type { HighlightState } from '../../hooks/useHighlight';

interface DocGraphProps {
  data: GraphDTO;
  highlight: HighlightState;
  onNodeClick?: (nodeId: string) => void;
  loading?: boolean;
}

const nodeTypes: NodeTypes = {
  docNode: DocNode,
};

// Simple force-like layout: arrange nodes in clusters by repo
function layoutNodes(graphNodes: GNode[]): Record<string, { x: number; y: number }> {
  const repos = [...new Set(graphNodes.map(n => n.repo))];
  const positions: Record<string, { x: number; y: number }> = {};
  const repoGroups: Record<string, GNode[]> = {};

  for (const n of graphNodes) {
    if (!repoGroups[n.repo]) repoGroups[n.repo] = [];
    repoGroups[n.repo].push(n);
  }

  const repoCount = repos.length;
  repos.forEach((repo, repoIdx) => {
    const nodes = repoGroups[repo];
    // Place repo clusters in a circular arrangement
    const angle = (repoIdx / repoCount) * Math.PI * 2 - Math.PI / 2;
    const clusterRadius = 260;
    const cx = 400 + Math.cos(angle) * clusterRadius;
    const cy = 320 + Math.sin(angle) * clusterRadius;

    nodes.forEach((node, i) => {
      const nodeAngle = (i / nodes.length) * Math.PI * 2;
      const innerRadius = 80 + nodes.length * 12;
      positions[node.id] = {
        x: cx + Math.cos(nodeAngle) * innerRadius,
        y: cy + Math.sin(nodeAngle) * innerRadius,
      };
    });
  });

  return positions;
}

function getEdgeStyle(type: string, highlighted: boolean): Partial<Edge> {
  const base: Partial<Edge> = {
    animated: false,
    style: {},
  };

  if (highlighted) {
    return {
      ...base,
      className: 'highlighted-edge',
      style: {
        stroke: '#8b5cf6',
        strokeWidth: 2,
        filter: 'drop-shadow(0 0 6px rgba(139,92,246,0.8))',
      },
      animated: true,
    };
  }

  switch (type) {
    case 'conflicts-with':
      return {
        ...base,
        className: 'conflict-edge',
        style: {
          stroke: '#ef4444',
          strokeWidth: 2.5,
          strokeDasharray: '6 3',
          filter: 'drop-shadow(0 0 4px rgba(239,68,68,0.5))',
        },
      };
    case 'duplicate-of':
      return {
        ...base,
        className: 'duplicate-edge',
        style: {
          stroke: '#f97316',
          strokeWidth: 1.5,
          strokeDasharray: '6 3',
        },
      };
    case 'deprecated-by':
      return {
        ...base,
        className: 'deprecated-edge',
        style: {
          stroke: '#6b7280',
          strokeWidth: 1,
          strokeDasharray: '4 4',
          opacity: 0.5,
        },
      };
    default: // references
      return {
        ...base,
        style: {
          stroke: 'rgba(148,163,184,0.4)',
          strokeWidth: 1.2,
        },
      };
  }
}

export function DocGraph({ data, highlight, onNodeClick, loading }: DocGraphProps) {
  const positions = useMemo(() => layoutNodes(data.nodes), [data.nodes]);

  const initialNodes: Node[] = useMemo(
    () =>
      data.nodes.map(gn => ({
        id: gn.id,
        type: 'docNode',
        position: positions[gn.id] ?? { x: 100, y: 100 },
        data: {
          ...gn,
          highlighted: highlight.nodeIds.has(gn.id),
        },
        selected: false,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data.nodes, positions],
  );

  const initialEdges: Edge[] = useMemo(
    () =>
      data.edges.map(ge => {
        const highlighted = highlight.edgeIds?.has(ge.id) ?? false;
        const edgeStyle = getEdgeStyle(ge.type, highlighted);
        return {
          id: ge.id,
          source: ge.source,
          target: ge.target,
          ...edgeStyle,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color:
              ge.type === 'conflicts-with'
                ? '#ef4444'
                : ge.type === 'duplicate-of'
                  ? '#f97316'
                  : 'rgba(148,163,184,0.5)',
            width: 8,
            height: 8,
          },
        };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data.edges],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync when data loads asynchronously (useNodesState/useEdgesState only use the value at mount)
  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  // Sync highlight changes without full re-mount
  const highlightedNodes = useMemo(() => {
    return nodes.map(n => ({
      ...n,
      data: {
        ...n.data,
        highlighted: highlight.nodeIds.has(n.id),
      },
    }));
  }, [nodes, highlight.nodeIds]);

  const highlightedEdges = useMemo(() => {
    return edges.map(e => {
      const highlighted = highlight.edgeIds?.has(e.id) ?? false;
      // Find original type
      const original = data.edges.find(de => de.id === e.id);
      const edgeStyle = getEdgeStyle(original?.type ?? 'references', highlighted);
      return { ...e, ...edgeStyle };
    });
  }, [edges, highlight.edgeIds, data.edges]);

  const onConnect: OnConnect = useCallback(
    () => setNodes(nds => nds.map(n => ({ ...n }))),
    [setNodes],
  );

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick],
  );

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background: '#0d0d12',
      }}
    >
      {/* Cosmic sparkle background */}
      <SparkleBackground />

      {/* Dot grid overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle, rgba(139,92,246,0.08) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
          pointerEvents: 'none',
          zIndex: 1,
        }}
      />

      {/* React Flow graph */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 2 }}>
        <ReactFlow
          nodes={highlightedNodes}
          edges={highlightedEdges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-right"
          style={{ background: 'transparent' }}
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{
            type: 'smoothstep',
          }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={32}
            size={1}
            color="rgba(139,92,246,0.05)"
            style={{ background: 'transparent' }}
          />
          <Controls
            style={{ bottom: 24, left: 16 }}
          />
          <MiniMap
            style={{ bottom: 24, right: 16, width: 160, height: 100 }}
            nodeColor={n => {
              const health = (n.data as { health?: string }).health;
              switch (health) {
                case 'green': return '#22d3a0';
                case 'yellow': return '#f59e0b';
                case 'red': return '#ef4444';
                default: return '#4b5563';
              }
            }}
            maskColor="rgba(13,13,18,0.8)"
          />
        </ReactFlow>
      </div>

      {/* Loading overlay */}
      {loading && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(13,13,18,0.7)',
            backdropFilter: 'blur(4px)',
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                border: '3px solid rgba(139,92,246,0.2)',
                borderTopColor: '#8b5cf6',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 12px',
              }}
            />
            <span style={{ color: 'rgba(226,232,240,0.6)', fontSize: 13 }}>
              Loading graph…
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
