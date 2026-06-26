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
  // ─── ACT 1 · The problem ──────────────────────────────────────────────
  {
    id: 'act1-slide',
    act: 1,
    caption: 'The problem: documentation rots — silently.',
    action: {
      kind: 'slide',
      kicker: 'Act 1 of 4 · The problem',
      title: 'Docs rot — silently',
      bullets: [
        'Teams trust documentation that has quietly gone stale',
        'Two pages disagree — and nobody notices',
        'The cost: wrong builds, lost hours, broken trust',
      ],
      visual: {
        kind: 'conflict',
        left: {
          title: 'docs/build.md',
          badge: 'canonical',
          tone: 'good',
          lines: ['Requires the .NET 8 SDK', '$ dotnet build -c Release'],
        },
        right: {
          title: 'docs/build-legacy.md',
          badge: 'stale',
          tone: 'bad',
          lines: ['Requires the .NET 6 SDK', '$ dotnet build'],
        },
        relation: 'conflicts-with',
      },
    },
    durationMs: 9000,
  },
  {
    id: 'graph',
    act: 1,
    caption: 'Meet your living knowledge graph — colour is health, size is importance.',
    cue: 'No human drew these links. The glowing red node is stale and conflicts with its canonical source.',
    spotlight: 'graph',
    action: { kind: 'highlight', pick: 'problem', focus: true, intensity: 0.95 },
    durationMs: 7000,
  },
  {
    id: 'select',
    act: 1,
    caption: 'DocGuardian flagged this page — stale and contradicting the canonical source.',
    cue: 'It picks out the conflicting document automatically — no one had to go looking.',
    spotlight: 'graph',
    action: { kind: 'selectDoc', pick: 'problem' },
    durationMs: 6000,
  },

  // ─── ACT 2 · Trustworthy answers ──────────────────────────────────────
  {
    id: 'act2-slide',
    act: 2,
    caption: 'Ask your docs anything — and trust the answer.',
    action: {
      kind: 'slide',
      kicker: 'Act 2 of 4 · Trustworthy answers',
      title: 'Evidence or silence',
      bullets: [
        'Ask in plain English',
        'A grounded answer with citations + a confidence score',
        'Weak evidence → an honest “needs review”, never a guess',
      ],
      visual: {
        kind: 'answer',
        question: 'How do I build Garnet from source?',
        answer: 'Use the .NET 8 SDK and run `dotnet build -c Release` from the repo root.',
        confidence: 0.82,
        citations: [
          { label: 'build.md', relevance: 0.91 },
          { label: 'README.md', relevance: 0.68 },
        ],
      },
    },
    durationMs: 9000,
  },
  {
    id: 'ask',
    act: 2,
    caption: 'A grounded answer — with citations and confidence, not a guess.',
    cue: 'Answers .NET 8 / dotnet build -c Release, cites build.md (~0.82). The sources it used glow on the graph.',
    spotlight: 'chat',
    action: { kind: 'chat', text: QUESTION },
    durationMs: 12000,
  },

  // ─── ACT 3 · Self-healing docs ────────────────────────────────────────
  {
    id: 'act3-slide',
    act: 3,
    caption: 'They patch the answer; we fix the source.',
    action: {
      kind: 'slide',
      kicker: 'Act 3 of 4 · Self-healing docs',
      title: 'Curator drafts · Guardian reviews',
      bullets: [
        'Detects stale, duplicate and conflicting docs',
        'The Curator proposes one canonical fix',
        'The Guardian reviews it against the evidence',
        'Nothing ships without a human approval',
      ],
      visual: {
        kind: 'diff',
        before: ['Requires the .NET 6 SDK.', 'dotnet build'],
        after: ['Requires the .NET 8 SDK.', 'dotnet build -c Release'],
        reviewer: 'Guardian',
        confidence: 0.79,
        status: 'Awaiting human approval',
      },
    },
    durationMs: 10000,
  },
  {
    id: 'doc-analysis',
    act: 3,
    caption: 'Per-document analysis: low quality, broken links, high staleness risk.',
    cue: "That's exactly why this node is flagged red.",
    spotlight: 'insights',
    action: { kind: 'openInsights', tab: 'doc', pick: 'problem' },
    durationMs: 8000,
  },
  {
    id: 'propose',
    act: 3,
    caption: 'One click proposes an evidence-backed fix.',
    cue: 'The Curator drafts one canonical version; the Guardian reviews it with evidence + a confidence score.',
    action: { kind: 'propose' },
    durationMs: 8000,
  },
  {
    id: 'diff',
    act: 3,
    caption: 'Every edit shows a diff, its sources, and a confidence score — evidence or silence.',
    cue: 'No grounded citation or low confidence → it routes to human review, never auto-applied.',
    action: { kind: 'caption' },
    durationMs: 9000,
  },
  {
    id: 'approve',
    act: 3,
    caption: 'A human approves — and provenance + rollback are recorded.',
    cue: 'Immutable audit: what changed, who approved, which agent, why. Watch the header metrics tick up.',
    spotlight: 'metrics',
    action: {
      kind: 'approve',
      metricsDelta: {
        staleFixed: 1,
        conflictsResolved: 1,
        duplicatesRemoved: 1,
        brokenLinksResolved: 2,
      },
    },
    durationMs: 8000,
  },

  // ─── ACT 4 · Governed & everywhere ────────────────────────────────────
  {
    id: 'act4-slide',
    act: 4,
    caption: 'Governed — and everywhere you already work.',
    action: {
      kind: 'slide',
      kicker: 'Act 4 of 4 · Governance & reach',
      title: 'Governed, and everywhere you work',
      bullets: [
        'Permissions enforced at retrieval, answer & write',
        'Full provenance + one-click rollback',
        'Insights: stale / duplicate / quality trends across the corpus',
        'The same grounded answers inside Copilot via MCP',
      ],
      visual: {
        kind: 'permission',
        docTitle: 'security/prod-oncall-secrets.md',
        badge: 'No access',
        note: 'Enforced at retrieval, answer & write — restricted content never reaches the model or the answer.',
        redactedLines: 3,
      },
    },
    durationMs: 10000,
  },
  {
    id: 'trends',
    act: 4,
    caption: 'Knowledge health you can manage — detected vs. fixed over time.',
    cue: 'Insights roll up stale, duplicate, broken-link and quality trends across the whole corpus.',
    spotlight: 'insights',
    action: { kind: 'openInsights', tab: 'corpus' },
    durationMs: 8000,
  },
  {
    id: 'mcp',
    act: 4,
    caption: 'The same grounded answers — right inside Copilot, via MCP.',
    action: {
      kind: 'slide',
      kicker: 'Act 4 of 4 · Everywhere you work',
      title: 'In your editor, not just our app',
      bullets: [
        'DocGuardian ships an MCP server',
        'Ask from Copilot — same evidence, same citations',
        'Permissions & provenance travel with the answer',
      ],
      visual: {
        kind: 'mcp',
        client: 'GitHub Copilot',
        prompt: 'How do I build Garnet from source?',
        answer: 'Use the .NET 8 SDK · `dotnet build -c Release`.',
        citations: ['build.md', 'README.md'],
      },
    },
    durationMs: 9000,
  },
  {
    id: 'outro',
    act: 4,
    caption: 'Detected, fixed with evidence, human-approved.',
    action: {
      kind: 'slide',
      kicker: 'DocGuardian AI',
      title: 'Copilot answers. Obsidian stores. DocGuardian governs.',
      bullets: [
        'Evidence-backed answers — or an honest “needs review”',
        'Self-healing docs with human approval & provenance',
        'Now it’s your turn: ask, drop in a doc, or open Insights',
      ],
      visual: {
        kind: 'stats',
        items: [
          { label: 'Stale fixed', value: '+1', tone: 'good' },
          { label: 'Conflicts resolved', value: '+1', tone: 'good' },
          { label: 'Duplicates removed', value: '+1', tone: 'good' },
          { label: 'Broken links fixed', value: '+2', tone: 'good' },
        ],
        footnote: 'Just now, in this demo — every change human-approved, with provenance + rollback.',
      },
    },
    durationMs: 9000,
  },
];
