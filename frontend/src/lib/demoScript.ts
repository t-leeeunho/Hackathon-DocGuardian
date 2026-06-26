import type { DemoBeat } from '../hooks/useDemo';

/**
 * The guided-demo storyline. Edit freely — order, captions (which double as the
 * presenter's talking-point cues), durations, and target docs. Doc ids match the
 * offline fixtures in `lib/fixtures.ts`, so the whole run works with the backend
 * down and never hits Azure.
 */

const CONFLICT_DOC = 'garnet/docs/build-legacy.md'; // red node: stale + conflicting
const QUESTION = 'How do I build Garnet from source?';

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
    cue: 'No human drew these links. The red node: build.md (.NET 8) vs a stale build-legacy.md (.NET 6).',
    action: {
      kind: 'highlight',
      nodeIds: ['garnet/docs/build.md', CONFLICT_DOC],
      focus: true,
      intensity: 0.95,
    },
    durationMs: 6000,
  },
  {
    id: 'select',
    caption: 'build-legacy.md is stale and conflicts with the canonical build guide.',
    cue: 'Selected the red .NET 6 page — watch the evidence and analysis panels open.',
    action: { kind: 'selectDoc', docId: CONFLICT_DOC },
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
    cue: "That's exactly why this node is red.",
    action: { kind: 'openInsights', tab: 'doc' },
    durationMs: 7000,
  },
  {
    id: 'propose',
    caption: 'They patch the answer; we fix the source — one click proposes an evidence-backed fix.',
    cue: "Curator drafts one canonical 'Building Garnet'; Guardian reviews it with evidence + a confidence score.",
    action: { kind: 'propose', docId: CONFLICT_DOC },
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
