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
  health: string;
  repo: string;
  accessible: boolean;
  /** Insights overlay fields (additive, optional). */
  qualityScore?: number;
  brokenLinkCount?: number;
  orphan?: boolean;
  centrality?: number;
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
const HIGHLIGHT_COLOR = '#ffffff';
// Node colors derived from document health status so the graph immediately
// communicates which docs need attention.
const HEALTH_COLOR: Record<string, string> = {
  green: '#34d399',   // healthy
  yellow: '#fbbf24',  // stale / needs attention
  red: '#f87171',     // conflicting / critical
  gray: '#94a3b8',    // unknown / unverified
};

const LINK_COLOR: Record<string, string> = {
  'conflicts-with': '#ef4444',
  'duplicate-of': '#f97316',
  'deprecated-by': '#64748b',
  sibling: '#64748b',
  references: '#64748b',
};

// react-force-graph hands callbacks its internal node/link objects; cast to ours.
function asNode(o: object): FGNode {
  return o as unknown as FGNode;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    c === '&' ? '&amp;' : c === '<' ? '&lt;' : c === '>' ? '&gt;' : c === '"' ? '&quot;' : '&#39;',
  );
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

// A floating text tag (project name) rendered as a three.js sprite.
function makeLabelSprite(text: string, color: string): THREE.Sprite {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
  const font = '700 64px Inter, system-ui, sans-serif';
  ctx.font = font;
  const pad = 30;
  canvas.width = Math.ceil(ctx.measureText(text).width + pad * 2);
  canvas.height = 64 + pad * 2;
  ctx.font = font; // resizing the canvas resets the context
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(8,8,14,0.55)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = color;
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  const worldW = 260;
  const scale = worldW / canvas.width;
  sprite.scale.set(canvas.width * scale, canvas.height * scale, 1);
  return sprite;
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

  // One labelled, well-separated 3D ball per project.
  const clusters = useMemo(() => {
    const repos = [...new Set(data.nodes.map((n) => n.repo))].sort();
    const counts: Record<string, number> = {};
    data.nodes.forEach((n) => {
      counts[n.repo] = (counts[n.repo] ?? 0) + 1;
    });
    const ringRadius = 360 + repos.length * 55;
    return repos.map((repo, i) => {
      const a = (i / Math.max(1, repos.length)) * Math.PI * 2;
      return {
        repo,
        color: REPO_PALETTE[i % REPO_PALETTE.length],
        count: counts[repo],
        ballR: 70 + Math.cbrt(counts[repo]) * 30,
        center: {
          x: Math.cos(a) * ringRadius,
          y: Math.sin(a) * ringRadius,
          z: (i % 2 === 0 ? 1 : -1) * (140 + i * 60),
        } as Vec3,
      };
    });
  }, [data]);

  // Build graph data only when the document set changes. Each project's nodes are
  // placed inside their own 3D ball (and the layout is frozen) so every project
  // reads as a clean round sphere; nodes share one color except conflicts (red).
  const graphData = useMemo(() => {
    const byRepo = new Map(clusters.map((c) => [c.repo, c]));
    const nodes: FGNode[] = data.nodes.map((n) => {
      const cl = byRepo.get(n.repo);
      const c = cl?.center ?? { x: 0, y: 0, z: 0 };
      const p = spherePoint(cl?.ballR ?? 80);
      return {
        id: n.id,
        name: `${n.label}  ·  ${n.repo}`,
        val: 1 + Math.max(0, Math.min(1, n.size)) * 3.5,
        color: HEALTH_COLOR[n.health] ?? HEALTH_COLOR.gray,
        health: n.health,
        repo: n.repo,
        accessible: n.accessible,
        qualityScore: n.qualityScore,
        brokenLinkCount: n.brokenLinkCount,
        orphan: n.orphan,
        centrality: n.centrality,
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
  }, [clusters, data]);

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
        1.1, // strength
        0.5, // radius
        0.55, // threshold (only bright white cited nodes bloom; grey stays calm)
      );
      composer.addPass(bloom);
      bloomAdded.current = true;
    } catch {
      /* bloom is best-effort */
    }
  }, [dims, graphData]);

  // The layout is frozen (no ticks), so fit the camera exactly once on load.
  // We use both a timeout fallback and onEngineStop (passed to ForceGraph3D) to
  // ensure zoomToFit fires even when physics ends before React's effect runs.
  const fittedRef = useRef(false);
  const handleEngineStop = useCallback(() => {
    if (fittedRef.current || graphData.nodes.length === 0) return;
    fgRef.current?.zoomToFit?.(700, 140);
    fittedRef.current = true;
  }, [graphData.nodes.length]);
  useEffect(() => {
    // Reset so a new dataset gets its own zoomToFit.
    fittedRef.current = false;
    if (graphData.nodes.length === 0) return;
    const t = setTimeout(() => {
      fgRef.current?.zoomToFit?.(700, 140);
      fittedRef.current = true;
    }, 800);
    return () => clearTimeout(t);
  }, [graphData]);

  // A surrounding starfield so it feels like a place in space, not flat black.
  const starsAdded = useRef(false);
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || starsAdded.current || graphData.nodes.length === 0) return;
    try {
      const scene = fg.scene?.();
      if (!scene) return;
      const count = 1800;
      const positions = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        // points on a large spherical shell surrounding the scene
        const r = 2600 + Math.random() * 1800;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      const mat = new THREE.PointsMaterial({
        color: 0x9fb4ff,
        size: 2.4,
        sizeAttenuation: true,
        transparent: true,
        opacity: 0.75,
        depthWrite: false,
      });
      scene.add(new THREE.Points(geo, mat));
      starsAdded.current = true;
    } catch {
      /* starfield is best-effort */
    }
  }, [graphData]);

  // Floating project-name tags above each cluster so they're easy to tell apart.
  const labelsAdded = useRef(false);
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || labelsAdded.current || clusters.length === 0) return;
    try {
      const scene = fg.scene?.();
      if (!scene) return;
      for (const cl of clusters) {
        const sprite = makeLabelSprite(cl.repo, cl.color);
        sprite.position.set(cl.center.x, cl.center.y + cl.ballR + 110, cl.center.z);
        scene.add(sprite);
      }
      labelsAdded.current = true;
    } catch {
      /* labels are best-effort */
    }
  }, [clusters]);

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

  // Re-tint/blink the cited nodes when the highlight changes, and — when the
  // highlight asks to `focus` (e.g. "Show traces") — fly the camera so the
  // cited nodes are centered in view.
  useEffect(() => {
    const fg = fgRef.current;
    fg?.refresh?.();

    if (!fg || !highlight.focus || highlight.nodeIds.size === 0) return;

    const targets = graphData.nodes.filter((n) => highlight.nodeIds.has(n.id));
    if (targets.length === 0) return;

    // Centroid of the cited nodes (positions are frozen after layout).
    const c = targets.reduce(
      (acc, n) => ({
        x: acc.x + (n.x ?? 0),
        y: acc.y + (n.y ?? 0),
        z: acc.z + (n.z ?? 0),
      }),
      { x: 0, y: 0, z: 0 },
    );
    c.x /= targets.length;
    c.y /= targets.length;
    c.z /= targets.length;

    // Pull the camera back along the direction from the scene origin through
    // the centroid so it looks inward at the cited cluster. Fall back to a
    // fixed direction when the centroid sits near the origin.
    const mag = Math.hypot(c.x, c.y, c.z) || 1;
    const dir =
      mag > 1e-3
        ? { x: c.x / mag, y: c.y / mag, z: c.z / mag }
        : { x: 0, y: 0, z: 1 };
    const distance = 420;
    const camPos = {
      x: c.x + dir.x * distance,
      y: c.y + dir.y * distance,
      z: c.z + dir.z * distance,
    };

    fg.cameraPosition?.(camPos, c, 900);
  }, [highlight, graphData]);

  const nodeColor = useCallback((node: object) => {
    const n = asNode(node);
    if (highlightRef.current.nodeIds.has(n.id)) return HIGHLIGHT_COLOR;
    if (!n.accessible) return '#3b3b44';
    return n.color;
  }, []);

  const nodeVal = useCallback((node: object) => {
    const n = asNode(node);
    return highlightRef.current.nodeIds.has(n.id) ? n.val * 3 : n.val;
  }, []);

  const linkColor = useCallback((link: object) => {
    const type = (link as unknown as FGLink).type;
    return LINK_COLOR[type] ?? LINK_COLOR.references;
  }, []);

  const linkWidth = useCallback((link: object) => {
    const type = (link as unknown as FGLink).type;
    return type === 'conflicts-with' || type === 'duplicate-of' ? 1.2 : 0.8;
  }, []);

  // Hover tooltip enriched with Insights (quality / centrality / broken / orphan).
  const nodeTooltip = useCallback((node: object) => {
    const n = asNode(node);
    const chips: string[] = [];
    if (n.qualityScore != null) chips.push(`quality ${Math.round(n.qualityScore * 100)}%`);
    if (n.centrality != null) chips.push(`centrality ${Math.round(n.centrality * 100)}%`);
    if (n.brokenLinkCount) chips.push(`${n.brokenLinkCount} broken link${n.brokenLinkCount > 1 ? 's' : ''}`);
    if (n.orphan) chips.push('orphan');
    if (!n.accessible) chips.push('locked');
    const meta = chips.length
      ? `<div style="color:#94a3b8;font-size:11px;margin-top:3px">${escapeHtml(chips.join('  ·  '))}</div>`
      : '';
    return (
      `<div style="padding:5px 9px;background:rgba(8,8,14,0.92);border:1px solid rgba(139,92,246,0.3);` +
      `border-radius:6px;color:#e2e8f0;font-size:12px;font-family:Inter,system-ui;box-shadow:0 4px 16px rgba(0,0,0,0.5)">` +
      `${escapeHtml(n.name)}${meta}</div>`
    );
  }, []);

  const handleClick = useCallback(
    (node: object) => {
      onNodeClick?.(asNode(node).id);
    },
    [onNodeClick],
  );

  // Return to the default fitted view after zooming/orbiting into a cluster.
  const handleResetView = useCallback(() => {
    fgRef.current?.zoomToFit?.(700, 140);
  }, []);

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%', height: '100%', background: '#000000' }}>
      {graphData.nodes.length > 0 && (
      <ForceGraph3D
        ref={fgRef}
        width={dims.width}
        height={dims.height}
        graphData={graphData}
        backgroundColor="#000000"
        showNavInfo={false}
        nodeLabel={nodeTooltip}
        nodeColor={nodeColor}
        nodeVal={nodeVal}
        nodeRelSize={4}
        nodeOpacity={0.95}
        nodeResolution={16}
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkOpacity={0.55}
        warmupTicks={0}
        cooldownTicks={0}
        onEngineStop={handleEngineStop}
        onNodeClick={handleClick}
      />
      )}

      {/* reset view */}
      {graphData.nodes.length > 0 && (
        <button
          type="button"
          onClick={handleResetView}
          title="Reset to default view"
          style={{
            position: 'absolute', top: 16, right: 16, zIndex: 6,
            display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
            borderRadius: 8, cursor: 'pointer',
            background: 'rgba(18,18,26,0.7)', border: '1px solid rgba(139,92,246,0.18)',
            color: '#cbd5e1', fontSize: 12, fontFamily: 'Inter, system-ui',
            backdropFilter: 'blur(8px)',
          }}
        >
          Reset view
        </button>
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
          [HEALTH_COLOR.green, 'healthy'], [HEALTH_COLOR.yellow, 'stale'], [HEALTH_COLOR.red, 'conflict'], ['#ffffff', 'cited'],
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
