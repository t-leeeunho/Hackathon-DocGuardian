import { describe, it, expect } from 'vitest';
import { fixtureGraph, fixtureChatAnswer, fixtureProposal, fixtureMetrics } from '../lib/fixtures';
import { fixtureAnalysisReport, fixtureTrends, fixtureDocAnalysis } from '../lib/fixtures';

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
