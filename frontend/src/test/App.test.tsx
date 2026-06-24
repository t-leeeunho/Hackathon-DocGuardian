import { describe, it, expect } from 'vitest';
import { fixtureGraph, fixtureChatAnswer, fixtureProposal, fixtureMetrics } from '../lib/fixtures';

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
