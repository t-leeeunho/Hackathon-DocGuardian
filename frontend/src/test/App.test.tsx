import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { fixtureGraph, fixtureChatAnswer, fixtureProposal, fixtureMetrics } from '../lib/fixtures';
import { fixtureAnalysisReport, fixtureTrends, fixtureDocAnalysis } from '../lib/fixtures';
import { demoScript, pickProblemTarget } from '../lib/demoScript';
import { SlideVisual } from '../components/demo/SlideVisual';

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
      // Spotlight beats may resolve their target dynamically (`pick`), in which
      // case there is no static docId/nodeIds to validate here.
      if (a.kind === 'selectDoc' && a.docId) expect(nodeIds.has(a.docId)).toBe(true);
      if (a.kind === 'propose' && a.docId) expect(nodeIds.has(a.docId)).toBe(true);
      if (a.kind === 'highlight' && a.nodeIds) {
        for (const id of a.nodeIds) expect(nodeIds.has(id)).toBe(true);
      }
      if (a.kind === 'chat') expect(a.text.trim().length).toBeGreaterThan(0);
    }
  });

  it('resolves a random problem doc from the live graph for the spotlight beats', () => {
    const target = pickProblemTarget(fixtureGraph);
    expect(target).not.toBeNull();
    expect(nodeIds.has(target!.docId)).toBe(true);
    for (const id of target!.partnerIds) expect(nodeIds.has(id)).toBe(true);
    expect(target!.partnerIds).not.toContain(target!.docId);

    // The picked node must be accessible (the permissions story must hold) and a
    // genuine "problem" — red, an orphan, or sitting on a conflicts-with edge.
    const node = fixtureGraph.nodes.find((n) => n.id === target!.docId)!;
    expect(node.accessible).not.toBe(false);
    const inConflict = fixtureGraph.edges.some(
      (e) =>
        e.type === 'conflicts-with' && (e.source === node.id || e.target === node.id),
    );
    expect(node.health === 'red' || node.orphan === true || inConflict).toBe(true);
  });

  it('drives the highlight + select spotlight beats off the dynamic pick', () => {
    const graph = demoScript.find((b) => b.id === 'graph')!;
    const select = demoScript.find((b) => b.id === 'select')!;
    const docAnalysis = demoScript.find((b) => b.id === 'doc-analysis')!;
    expect(graph.action.kind === 'highlight' && graph.action.pick).toBe('problem');
    expect(select.action.kind === 'selectDoc' && select.action.pick).toBe('problem');
    // The doc-analysis beat re-selects the problem doc so its analysis always
    // shows, even if the earlier select beat ran before the graph had loaded.
    expect(docAnalysis.action.kind === 'openInsights' && docAnalysis.action.pick).toBe(
      'problem',
    );
  });

  it('returns null when the graph has no nodes', () => {
    expect(pickProblemTarget({ nodes: [], edges: [] })).toBeNull();
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

  it('is structured as four acts, each opened by a presentation slide', () => {
    const acts = [1, 2, 3, 4];
    for (const act of acts) {
      const beats = demoScript.filter((b) => b.act === act);
      expect(beats.length).toBeGreaterThan(0);
      // The first beat of every act is a full-screen slide (mini-presentation).
      expect(beats[0].action.kind).toBe('slide');
    }
    // Every beat belongs to one of the four acts.
    for (const beat of demoScript) {
      expect(acts).toContain(beat.act);
    }
  });

  it('every slide has a headline and at least two bullets', () => {
    const slides = demoScript.filter((b) => b.action.kind === 'slide');
    expect(slides.length).toBeGreaterThanOrEqual(4);
    for (const s of slides) {
      if (s.action.kind === 'slide') {
        expect(s.action.title.length).toBeGreaterThan(0);
        expect(s.action.bullets.length).toBeGreaterThanOrEqual(2);
      }
    }
  });

  it('only spotlights known functional regions', () => {
    const known = new Set(['graph', 'chat', 'intake', 'insights', 'metrics']);
    for (const beat of demoScript) {
      if (beat.spotlight) expect(known.has(beat.spotlight)).toBe(true);
    }
  });

  it('starts and ends on a slide so the presentation book-ends cleanly', () => {
    expect(demoScript[0].action.kind).toBe('slide');
    expect(demoScript[demoScript.length - 1].action.kind).toBe('slide');
  });
});

describe('slide proof visuals', () => {
  function slideVisual(id: string) {
    const beat = demoScript.find((b) => b.id === id);
    expect(beat, `beat ${id} exists`).toBeDefined();
    if (beat!.action.kind !== 'slide') throw new Error(`${id} is not a slide`);
    return beat!.action.visual;
  }

  it('each act slide carries a concrete "show, don\'t tell" proof visual', () => {
    expect(slideVisual('act1-slide')?.kind).toBe('conflict');
    expect(slideVisual('act2-slide')?.kind).toBe('answer');
    expect(slideVisual('act3-slide')?.kind).toBe('diff');
    expect(slideVisual('act4-slide')?.kind).toBe('permission');
    expect(slideVisual('mcp')?.kind).toBe('mcp');
    expect(slideVisual('outro')?.kind).toBe('stats');
  });

  it('every slide beat now backs its claim with a proof visual', () => {
    for (const beat of demoScript) {
      if (beat.action.kind === 'slide') {
        expect(beat.action.visual, `slide ${beat.id} has a visual`).toBeDefined();
      }
    }
  });

  it('visual evidence matches the demo fixtures (slide preview == live demo)', () => {
    const answer = slideVisual('act2-slide');
    expect(answer?.kind).toBe('answer');
    if (answer?.kind === 'answer') {
      expect(answer.confidence).toBe(fixtureChatAnswer.confidence);
      const fixtureRel = fixtureChatAnswer.citations.map((c) => c.relevance);
      for (const c of answer.citations) expect(fixtureRel).toContain(c.relevance);
    }
    const diff = slideVisual('act3-slide');
    expect(diff?.kind).toBe('diff');
    if (diff?.kind === 'diff') {
      expect(diff.confidence).toBe(fixtureProposal.confidence);
    }
  });

  it('renders the Act 1 conflict (the real .NET 8 vs .NET 6 disagreement)', () => {
    render(<SlideVisual visual={slideVisual('act1-slide')!} />);
    expect(screen.getByText(/conflicts-with/)).toBeInTheDocument();
    expect(screen.getByText(/\.NET 8 SDK/)).toBeInTheDocument();
    expect(screen.getByText(/\.NET 6 SDK/)).toBeInTheDocument();
  });

  it('renders the Act 2 grounded answer with citations + confidence', () => {
    render(<SlideVisual visual={slideVisual('act2-slide')!} />);
    expect(screen.getByText('build.md')).toBeInTheDocument();
    expect(screen.getByText(/confidence 82%/)).toBeInTheDocument();
  });

  it('renders the Act 3 diff under Guardian review, awaiting approval', () => {
    render(<SlideVisual visual={slideVisual('act3-slide')!} />);
    expect(screen.getByText(/Guardian/)).toBeInTheDocument();
    expect(screen.getByText('Awaiting human approval')).toBeInTheDocument();
  });

  it('renders the closing scoreboard of what the demo just fixed', () => {
    render(<SlideVisual visual={slideVisual('outro')!} />);
    expect(screen.getByText('+2')).toBeInTheDocument();
    expect(screen.getByText('Broken links fixed')).toBeInTheDocument();
  });

  it('renders the Act 4 permission proof — a locked node whose content is never shown', () => {
    render(<SlideVisual visual={slideVisual('act4-slide')!} />);
    expect(screen.getByText('security/prod-oncall-secrets.md')).toBeInTheDocument();
    expect(screen.getByText('No access')).toBeInTheDocument();
    expect(screen.getByText(/never reaches the model/)).toBeInTheDocument();
  });

  it('renders the MCP proof — the same cited answer inside Copilot', () => {
    render(<SlideVisual visual={slideVisual('mcp')!} />);
    expect(screen.getByText('@docguardian')).toBeInTheDocument();
    expect(screen.getByText(/via DocGuardian MCP/)).toBeInTheDocument();
    expect(screen.getByText('build.md')).toBeInTheDocument();
  });
});
