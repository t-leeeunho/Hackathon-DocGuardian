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
    caption: 'DocGuardian keeps engineering docs trustworthy as the code changes.',
    cue: 'Set the scene: docs rot silently — we detect and fix them with evidence.',
    action: { kind: 'caption' },
    durationMs: 5000,
  },
  {
    id: 'graph',
    caption: 'This is the live documentation graph — colour is health, size is importance.',
    cue: 'Point at the red node: a real conflict between two build guides.',
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
    caption: 'This document is stale and conflicts with the canonical build guide.',
    cue: 'We selected build-legacy.md — watch the panels open.',
    action: { kind: 'selectDoc', docId: CONFLICT_DOC },
    durationMs: 5000,
  },
  {
    id: 'ask',
    caption: 'Ask in plain English — answers are grounded in real document evidence.',
    cue: 'It types the question, cites its sources, and blinks them on the graph.',
    action: { kind: 'chat', text: QUESTION },
    durationMs: 11000,
  },
  {
    id: 'trends',
    caption: 'Insights: stale, duplicate, broken-link and quality trends across the corpus.',
    cue: 'Impact at a glance — detected vs. fixed over time.',
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
    caption: 'One click asks the agents to propose an evidence-backed fix.',
    cue: 'The Curator drafts the change; the Guardian reviews it.',
    action: { kind: 'propose', docId: CONFLICT_DOC },
    durationMs: 7000,
  },
  {
    id: 'diff',
    caption: 'Every edit shows a diff, its sources, and a confidence score — evidence or silence.',
    cue: 'No grounded citation, or low confidence → it routes to human review instead.',
    action: { kind: 'caption' },
    durationMs: 8000,
  },
  {
    id: 'approve',
    caption: 'A human approves — the change is applied and full provenance is recorded.',
    cue: 'Watch the metrics in the header tick up.',
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
    caption: 'Trustworthy docs: detected, fixed with evidence, and always human-approved.',
    cue: 'Recap the value and hand back to questions.',
    action: { kind: 'caption' },
    durationMs: 6000,
  },
];
