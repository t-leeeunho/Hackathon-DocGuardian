import { describe, it, expect } from 'vitest';
import { fixtureGraph, fixtureChatAnswer, fixtureProposal, fixtureMetrics } from '../lib/fixtures';
import { fixtureAnalysisReport, fixtureTrends, fixtureDocAnalysis } from '../lib/fixtures';
import { demoScript } from '../lib/demoScript';

describe('fixtures', () => {
  it('fixture graph has nodes and edges', () => {
    expect(fixtureGraph.nodes.length).toBeGreaterThan(0);
    expect(fixtureGraph.edges.length).toBeGreaterThan(0);
  });

  it('fixture graph has at least one conflicts-with edge', () => {
    const conflictEdge = fixtureGraph.edges.find(e => e.type === 'conflicts-with');
    expect(conflictEdge).toBeDefined();
  });

  it('fixture chat answer has citations', () => {
    expect(fixtureChatAnswer.citations.length).toBeGreaterThan(0);
    expect(fixtureChatAnswer.confidence).toBeGreaterThan(0);
    expect(fixtureChatAnswer.confidence).toBeLessThanOrEqual(1);
  });

  it('fixture proposal has required fields', () => {
    expect(fixtureProposal.action).toBeDefined();
    expect(fixtureProposal.draft).toBeTruthy();
    expect(fixtureProposal.confidence).toBeGreaterThanOrEqual(0);
  });

  it('fixture metrics has all required fields', () => {
    expect(fixtureMetrics.staleDetected).toBeGreaterThanOrEqual(0);
    expect(fixtureMetrics.duplicatesRemoved).toBeGreaterThanOrEqual(0);
    expect(fixtureMetrics.conflictsDetected).toBeGreaterThanOrEqual(0);
  });
});

describe('types validation', () => {
  it('graph nodes have health values', () => {
    const validHealthValues = new Set(['green', 'yellow', 'red', 'gray']);
    for (const node of fixtureGraph.nodes) {
      expect(validHealthValues.has(node.health)).toBe(true);
    }
  });

  it('graph edges have valid type values', () => {
    const validEdgeTypes = new Set(['references', 'duplicate-of', 'conflicts-with', 'deprecated-by']);
    for (const edge of fixtureGraph.edges) {
      expect(validEdgeTypes.has(edge.type)).toBe(true);
    }
  });

  it('citation relevance is between 0 and 1', () => {
    for (const citation of fixtureChatAnswer.citations) {
      expect(citation.relevance).toBeGreaterThanOrEqual(0);
      expect(citation.relevance).toBeLessThanOrEqual(1);
    }
  });
});

describe('insights fixtures (Analysis subsystem)', () => {
  it('corpus report exposes aggregates and worst-offender lists', () => {
    expect(fixtureAnalysisReport.totalDocs).toBeGreaterThan(0);
    expect(fixtureAnalysisReport.qualityAvg).toBeGreaterThanOrEqual(0);
    expect(fixtureAnalysisReport.qualityAvg).toBeLessThanOrEqual(1);
    expect(fixtureAnalysisReport.worstQuality.length).toBeGreaterThan(0);
    expect(fixtureAnalysisReport.mostAtRisk.length).toBeGreaterThan(0);
    expect(fixtureAnalysisReport.topCentral.length).toBeGreaterThan(0);
    for (const ref of fixtureAnalysisReport.mostAtRisk) {
      expect(ref.docId).toBeTruthy();
      expect(ref.score).toBeGreaterThanOrEqual(0);
      expect(Array.isArray(ref.reasons)).toBe(true);
    }
  });

  it('trends fixture has a time-series, histogram and rates in range', () => {
    expect(fixtureTrends.series.length).toBeGreaterThan(0);
    expect(fixtureTrends.confidenceHistogram.length).toBeGreaterThan(0);
    expect(fixtureTrends.byRepo.length).toBeGreaterThan(0);
    expect(fixtureTrends.proposalAcceptanceRate).toBeGreaterThanOrEqual(0);
    expect(fixtureTrends.proposalAcceptanceRate).toBeLessThanOrEqual(1);
    expect(fixtureTrends.evidenceCoverage).toBeGreaterThanOrEqual(0);
    expect(fixtureTrends.evidenceCoverage).toBeLessThanOrEqual(1);
    for (const pt of fixtureTrends.series) {
      // Fixes should never exceed detections in a coherent narrative.
      expect(pt.staleFixed).toBeLessThanOrEqual(pt.staleDetected);
      expect(pt.conflictsResolved).toBeLessThanOrEqual(pt.conflictsDetected);
    }
  });

  it('per-doc analysis fixtures carry quality/links/drift/centrality with null LLM notes', () => {
    const entries = Object.values(fixtureDocAnalysis);
    expect(entries.length).toBeGreaterThan(0);
    for (const a of entries) {
      expect(a.quality.qualityScore).toBeGreaterThanOrEqual(0);
      expect(a.quality.qualityScore).toBeLessThanOrEqual(1);
      expect(Array.isArray(a.quality.issues)).toBe(true);
      expect(a.links.brokenLinkCount).toBe(a.links.brokenInternal.length);
      expect(a.drift.riskScore).toBeGreaterThanOrEqual(0);
      expect(a.centrality).toBeGreaterThanOrEqual(0);
      // LLM notes are opt-in (fetched on demand), so the offline fixtures omit them.
      expect(a.llm ?? null).toBeNull();
    }
  });
});

describe('guided demo script', () => {
  const nodeIds = new Set(fixtureGraph.nodes.map((n) => n.id));

  it('has beats, each with a caption and an action', () => {
    expect(demoScript.length).toBeGreaterThan(0);
    for (const beat of demoScript) {
      expect(beat.id).toBeTruthy();
      expect(beat.caption.length).toBeGreaterThan(0);
      expect(beat.action.kind).toBeTruthy();
    }
  });

  it('has unique beat ids', () => {
    const ids = demoScript.map((b) => b.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('references only real fixture documents (no typos that would break the live run)', () => {
    for (const beat of demoScript) {
      const a = beat.action;
      if (a.kind === 'selectDoc') expect(nodeIds.has(a.docId)).toBe(true);
      if (a.kind === 'propose' && a.docId) expect(nodeIds.has(a.docId)).toBe(true);
      if (a.kind === 'highlight') for (const id of a.nodeIds) expect(nodeIds.has(id)).toBe(true);
      if (a.kind === 'chat') expect(a.text.trim().length).toBeGreaterThan(0);
    }
  });

  it('approves exactly once and bumps the metrics', () => {
    const approvals = demoScript.filter((b) => b.action.kind === 'approve');
    expect(approvals.length).toBe(1);
    const a = approvals[0].action;
    if (a.kind === 'approve') {
      expect(a.metricsDelta).toBeDefined();
      expect(Object.keys(a.metricsDelta ?? {}).length).toBeGreaterThan(0);
    }
  });
});
