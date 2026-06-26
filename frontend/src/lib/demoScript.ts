import type { DemoBeat, DemoTarget } from '../hooks/useDemo';
import type { GraphDTO } from './types';

/**
 * The guided-demo storyline. Edit freely — order, captions (which double as the
 * presenter's talking-point cues), and durations. The spotlight beats (`graph`,
 * `select`, `propose`) no longer hard-code a doc: they pick a random *problem*
 * node from the live graph at run time (see `pickProblemTarget`), so the captions
 * stay generic and the run works with the backend down and never hits Azure.
 */

const QUESTION = 'How do I build Garnet from source?';

/** Edge types that signal a node sits in a conflict/duplicate relationship. */
const CONFLICT_EDGE_TYPES = new Set<string>([
  'conflicts-with',
  'duplicate-of',
  'deprecated-by',
]);

/**
 * Pick a random *problem* document from the current graph — one that is flagged
 * red, an orphan, or sitting on a `conflicts-with` edge — so the guided demo
 * spotlights a genuinely stale/conflicting node instead of a single hard-coded
 * one. Inaccessible nodes are skipped (the permissions story must hold). The
 * chosen node's conflict/duplicate partners (the other end of those edges) are
 * returned too, so the highlight can show the relationship. Returns `null` only
 * when the graph has no usable nodes.
 */
export function pickProblemTarget(graph: GraphDTO): DemoTarget | null {
  const nodes = graph.nodes ?? [];
  const edges = graph.edges ?? [];
  if (nodes.length === 0) return null;

  const inConflict = new Set<string>();
  for (const e of edges) {
    if (e.type !== 'conflicts-with') continue;
    inConflict.add(e.source);
    inConflict.add(e.target);
  }

  const accessible = nodes.filter((n) => n.accessible !== false);
  const candidates = accessible.filter(
    (n) => n.health === 'red' || n.orphan === true || inConflict.has(n.id),
  );
  const pool = candidates.length > 0 ? candidates : accessible;
  if (pool.length === 0) return null;

  const chosen = pool[Math.floor(Math.random() * pool.length)];

  const partners = new Set<string>();
  for (const e of edges) {
    if (!CONFLICT_EDGE_TYPES.has(e.type)) continue;
    if (e.source === chosen.id) partners.add(e.target);
    else if (e.target === chosen.id) partners.add(e.source);
  }
  partners.delete(chosen.id);

  return { docId: chosen.id, partnerIds: [...partners] };
}

export const demoScript: DemoBeat[] = [
  {
    id: 'intro',
    caption: 'Copilot answers your docs. Obsidian stores them. DocGuardian governs them.',
    cue: 'Hook: docs rot silently and contradict each other — we detect and fix them with evidence.',
    action: { kind: 'caption' },
    durationMs: 5000,
  },
  {
    id: 'graph',
    caption: 'The live knowledge graph — colour is health, size is importance.',
    cue: 'No human drew these links. DocGuardian flags two sources that disagree — a conflict it caught on its own.',
    action: {
      kind: 'highlight',
      pick: 'problem',
      focus: true,
      intensity: 0.95,
    },
    durationMs: 6000,
  },
  {
    id: 'select',
    caption: 'A flagged document — stale and conflicting with another source in the corpus.',
    cue: 'Selected the flagged page — watch the evidence and analysis panels open.',
    action: { kind: 'selectDoc', pick: 'problem' },
    durationMs: 5000,
  },
  {
    id: 'ask',
    caption: 'Ask in plain English — a grounded answer with citations and confidence, not a guess.',
    cue: 'Answers .NET 8 / dotnet build -c Release, cites build.md (~0.82), blinks sources on the graph. Evidence or silence.',
    action: { kind: 'chat', text: QUESTION },
    durationMs: 11000,
  },
  {
    id: 'trends',
    caption: 'Insights: stale, duplicate, broken-link and quality trends across the corpus.',
    cue: 'Knowledge health you can manage — detected vs. fixed over time.',
    action: { kind: 'openInsights', tab: 'corpus' },
    durationMs: 7000,
  },
  {
    id: 'doc-analysis',
    caption: 'Per-document analysis: low quality score, broken links, high staleness risk.',
    cue: "That's exactly why this node is flagged.",
    action: { kind: 'openInsights', tab: 'doc' },
    durationMs: 7000,
  },
  {
    id: 'propose',
    caption: 'They patch the answer; we fix the source — one click proposes an evidence-backed fix.',
    cue: 'Curator drafts one canonical version; Guardian reviews it with evidence + a confidence score.',
    action: { kind: 'propose' },
    durationMs: 7000,
  },
  {
    id: 'diff',
    caption: 'Every edit shows a diff, its sources, and a confidence score — evidence or silence.',
    cue: 'No grounded citation or low confidence → routes to human review, never auto-applied.',
    action: { kind: 'caption' },
    durationMs: 8000,
  },
  {
    id: 'approve',
    caption: 'Nothing changes without a human — approve, and provenance + rollback are recorded.',
    cue: 'Immutable audit: what changed, who approved, which agent, why. Watch the header metrics tick up.',
    action: {
      kind: 'approve',
      metricsDelta: {
        staleFixed: 1,
        conflictsResolved: 1,
        duplicatesRemoved: 1,
        brokenLinksResolved: 2,
      },
    },
    durationMs: 7000,
  },
  {
    id: 'outro',
    caption: 'Detected, fixed with evidence, human-approved — same answer inside Copilot via MCP.',
    cue: 'Close: Copilot answers. Obsidian stores. DocGuardian governs.',
    action: { kind: 'caption' },
    durationMs: 6000,
  },
];
