import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import type { GraphDTO } from '../../lib/types';
import type { HighlightState } from '../../hooks/useHighlight';

interface DocGraphProps {
  data: GraphDTO;
  highlight: HighlightState;
  onNodeClick?: (nodeId: string) => void;
  loading?: boolean;
}

/** Node shape we feed to the force graph. */
interface FGNode {
  id: string;
  name: string;
  val: number;
  color: string;
  repo: string;
  accessible: boolean;
  x?: number;
  y?: number;
  z?: number;
}
interface FGLink {
  source: string;
  target: string;
  type: string;
}

// One vivid color per project; conflicts override to a single shared red so they
// pop no matter which project they live in.
const REPO_PALETTE = [
  '#60a5fa', '#22d3ee', '#a78bfa', '#f472b6',
  '#34d399', '#fbbf24', '#fb923c', '#818cf8', '#2dd4bf', '#e879f9',
];
const CONFLICT_COLOR = '#ef4444';
const HIGHLIGHT_COLOR = '#ffffff';

const LINK_COLOR: Record<string, string> = {
  'conflicts-with': '#f87171',
  'duplicate-of': '#fb923c',
  'deprecated-by': '#9ca3af',
  sibling: 'rgba(148,163,184,0.35)',
  references: 'rgba(148,163,184,0.55)',
};

// react-force-graph hands callbacks its internal node/link objects; cast to ours.
function asNode(o: object): FGNode {
  return o as unknown as FGNode;
}

type Vec3 = { x: number; y: number; z: number };

// A uniformly-random point inside a ball of the given radius.
function spherePoint(radius: number): Vec3 {
  const u = Math.random();
  const v = Math.random();
  const theta = 2 * Math.PI * u;
  const phi = Math.acos(2 * v - 1);
  const r = radius * Math.cbrt(Math.random());
  return {
    x: r * Math.sin(phi) * Math.cos(theta),
    y: r * Math.sin(phi) * Math.sin(theta),
    z: r * Math.cos(phi),
  };
}

export function DocGraph({ data, highlight, onNodeClick, loading }: DocGraphProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });

  // Keep the latest highlight in a ref so the color/size accessors can read it
  // without rebuilding graphData (which would reheat the simulation).
  const highlightRef = useRef(highlight);
  highlightRef.current = highlight;

  // Build graph data only when the document set changes. Each project's nodes are
  // placed inside their own 3D ball (and the layout is frozen) so every project
  // reads as a clean round sphere instead of a stringy force-stretched mess.
  const graphData = useMemo(() => {
    const repos = [...new Set(data.nodes.map((n) => n.repo))].sort();
    const repoColor: Record<string, string> = {};
    const centers: Record<string, Vec3> = {};
    const counts: Record<string, number> = {};
    data.nodes.forEach((n) => {
      counts[n.repo] = (counts[n.repo] ?? 0) + 1;
    });
    const ringRadius = 360 + repos.length * 55;
    repos.forEach((r, i) => {
      repoColor[r] = REPO_PALETTE[i % REPO_PALETTE.length];
      const a = (i / Math.max(1, repos.length)) * Math.PI * 2;
      centers[r] = {
        x: Math.cos(a) * ringRadius,
        y: Math.sin(a) * ringRadius,
        z: (i % 2 === 0 ? 1 : -1) * (140 + i * 60),
      };
    });
    const nodes: FGNode[] = data.nodes.map((n) => {
      const c = centers[n.repo] ?? { x: 0, y: 0, z: 0 };
      const ballR = 70 + Math.cbrt(counts[n.repo] ?? 1) * 30;
      const p = spherePoint(ballR);
      return {
        id: n.id,
        name: `${n.label}  ·  ${n.repo}`,
        val: 1 + Math.max(0, Math.min(1, n.size)) * 6,
        // conflict (red health) is uniform; everything else is its project color.
        color: n.health === 'red' ? CONFLICT_COLOR : repoColor[n.repo] ?? '#94a3b8',
        repo: n.repo,
        accessible: n.accessible,
        x: c.x + p.x,
        y: c.y + p.y,
        z: c.z + p.z,
      };
    });
    const ids = new Set(nodes.map((n) => n.id));
    const links: FGLink[] = data.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((e) => ({ source: e.source, target: e.target, type: e.type }));
    return { nodes, links };
  }, [data]);

  // One well-separated 3D center per repo is applied by seeding node positions
  // (see graphData above). No runtime d3 force manipulation — that races the
  // library's animation loop and crashes.

  // Add a bloom pass once so bright nodes glow/sparkle (the celestial look).
  const bloomAdded = useRef(false);
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || bloomAdded.current) return;
    try {
      const composer = fg.postProcessingComposer?.();
      if (!composer) return;
      const bloom = new UnrealBloomPass(
        new THREE.Vector2(dims.width, dims.height),
        0.7, // strength (subtle glow, not a white-out)
        0.45, // radius
        0.35, // threshold (only the brightest cores bloom)
      );
      composer.addPass(bloom);
      bloomAdded.current = true;
    } catch {
      /* bloom is best-effort */
    }
  }, [dims, graphData]);

  // The layout is frozen (no ticks), so fit the camera once nodes are placed.
  useEffect(() => {
    if (graphData.nodes.length === 0) return;
    const t = setTimeout(() => fgRef.current?.zoomToFit?.(700, 140), 500);
    return () => clearTimeout(t);
  }, [graphData]);

  // Responsive sizing.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => setDims({ width: el.clientWidth, height: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Re-tint nodes when the highlight changes (no re-layout).
  useEffect(() => {
    fgRef.current?.refresh?.();
  }, [highlight]);

  const nodeColor = useCallback((node: object) => {
    const n = asNode(node);
    if (highlightRef.current.nodeIds.has(n.id)) return HIGHLIGHT_COLOR;
    if (!n.accessible) return '#3b3b44';
    return n.color;
  }, []);

  const nodeVal = useCallback((node: object) => {
    const n = asNode(node);
    return highlightRef.current.nodeIds.has(n.id) ? n.val * 2.2 : n.val;
  }, []);

  const linkColor = useCallback((link: object) => {
    const type = (link as unknown as FGLink).type;
    return LINK_COLOR[type] ?? LINK_COLOR.references;
  }, []);

  const linkWidth = useCallback((link: object) => {
    const type = (link as unknown as FGLink).type;
    return type === 'references' || type === 'sibling' ? 0.7 : 2;
  }, []);

  // Flowing particles on conflict/duplicate links so they're easy to spot.
  const linkParticles = useCallback((link: object) => {
    const type = (link as unknown as FGLink).type;
    return type === 'conflicts-with' || type === 'duplicate-of' ? 3 : 0;
  }, []);

  const handleClick = useCallback(
    (node: object) => {
      onNodeClick?.(asNode(node).id);
    },
    [onNodeClick],
  );

  // Fit the camera once the layout settles.
  const handleEngineStop = useCallback(() => {
    fgRef.current?.zoomToFit?.(600, 80);
  }, []);

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%', height: '100%', background: '#0d0d12' }}>
      {graphData.nodes.length > 0 && (
      <ForceGraph3D
        ref={fgRef}
        width={dims.width}
        height={dims.height}
        graphData={graphData}
        backgroundColor="#0d0d12"
        showNavInfo={false}
        nodeLabel="name"
        nodeColor={nodeColor}
        nodeVal={nodeVal}
        nodeRelSize={5}
        nodeOpacity={0.95}
        nodeResolution={12}
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkOpacity={0.8}
        linkDirectionalParticles={linkParticles}
        linkDirectionalParticleWidth={1.8}
        linkDirectionalParticleSpeed={0.006}
        warmupTicks={0}
        cooldownTicks={0}
        onEngineStop={handleEngineStop}
        onNodeClick={handleClick}
      />
      )}

      {/* legend */}
      <div
        style={{
          position: 'absolute', bottom: 16, left: 16, zIndex: 5,
          display: 'flex', gap: 12, padding: '6px 12px', borderRadius: 8,
          background: 'rgba(18,18,26,0.7)', border: '1px solid rgba(139,92,246,0.18)',
          fontSize: 11, color: '#94a3b8', backdropFilter: 'blur(8px)',
        }}
      >
        {[
          ['#60a5fa', 'each color = a project'], ['#ef4444', 'conflict'], ['#ffffff', 'cited'],
        ].map(([c, label]) => (
          <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, boxShadow: `0 0 6px ${c}` }} />
            {label}
          </span>
        ))}
        <span style={{ color: '#475569' }}>drag to orbit · scroll to zoom</span>
      </div>

      {loading && (
        <div
          style={{
            position: 'absolute', inset: 0, zIndex: 10, display: 'flex',
            alignItems: 'center', justifyContent: 'center', background: 'rgba(13,13,18,0.7)',
          }}
        >
          <div style={{ textAlign: 'center', color: '#94a3b8' }}>
            <div
              style={{
                width: 40, height: 40, borderRadius: '50%', margin: '0 auto 12px',
                border: '3px solid rgba(139,92,246,0.2)', borderTopColor: '#8b5cf6',
                animation: 'spin 1s linear infinite',
              }}
            />
            <div style={{ fontSize: 12 }}>Loading graph…</div>
          </div>
        </div>
      )}
    </div>
  );
}
