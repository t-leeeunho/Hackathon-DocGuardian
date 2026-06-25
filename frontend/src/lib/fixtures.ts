/**
 * Demo fixtures — used when the backend is unreachable (offline/demo mode) and
 * for the governance-dependent panels (metrics, proposal review) that have no
 * live endpoint yet. They model a small, deliberately conflicted corpus so the
 * stale / duplicate / conflict story is visible without a running database.
 */
import type {
  AgentProposal,
  AnalysisReport,
  ChatAnswer,
  DocAnalysis,
  GraphDTO,
  MetricsDTO,
  TreeNode,
  TrendsDTO,
} from './types';

export const fixtureGraph: GraphDTO = {
  nodes: [
    { id: 'garnet/README.md', label: 'README.md', health: 'green', size: 0.9, accessible: true, repo: 'garnet', qualityScore: 0.88, brokenLinkCount: 0, orphan: false, centrality: 0.92 },
    { id: 'garnet/docs/build.md', label: 'build.md', health: 'yellow', size: 0.6, accessible: true, repo: 'garnet', qualityScore: 0.66, brokenLinkCount: 1, orphan: false, centrality: 0.45 },
    { id: 'garnet/docs/build-legacy.md', label: 'build-legacy.md', health: 'red', size: 0.5, accessible: true, repo: 'garnet', qualityScore: 0.34, brokenLinkCount: 2, orphan: true, centrality: 0.08 },
    { id: 'playwright/docs/intro.md', label: 'intro.md', health: 'green', size: 0.8, accessible: true, repo: 'playwright', qualityScore: 0.81, brokenLinkCount: 0, orphan: false, centrality: 0.74 },
    { id: 'playwright/docs/codegen.md', label: 'codegen.md', health: 'green', size: 0.55, accessible: true, repo: 'playwright', qualityScore: 0.6, brokenLinkCount: 0, orphan: false, centrality: 0.3 },
    { id: 'onnxruntime/docs/install.md', label: 'install.md', health: 'yellow', size: 0.7, accessible: true, repo: 'onnxruntime', qualityScore: 0.7, brokenLinkCount: 0, orphan: false, centrality: 0.66 },
    { id: 'onnxruntime/docs/install-old.md', label: 'install-old.md', health: 'gray', size: 0.4, accessible: false, repo: 'onnxruntime', qualityScore: 0.41, brokenLinkCount: 1, orphan: true, centrality: 0.05 },
    { id: 'vscode/docs/setup.md', label: 'setup.md', health: 'green', size: 0.75, accessible: true, repo: 'vscode', qualityScore: 0.78, brokenLinkCount: 0, orphan: false, centrality: 0.2 },
  ],
  edges: [
    { id: 'e1', source: 'garnet/README.md', target: 'garnet/docs/build.md', type: 'references', weight: 1 },
    { id: 'e2', source: 'garnet/docs/build.md', target: 'garnet/docs/build-legacy.md', type: 'conflicts-with', weight: 0.88 },
    { id: 'e3', source: 'onnxruntime/docs/install.md', target: 'onnxruntime/docs/install-old.md', type: 'duplicate-of', weight: 0.94 },
    { id: 'e4', source: 'onnxruntime/docs/install-old.md', target: 'onnxruntime/docs/install.md', type: 'deprecated-by', weight: 0.7 },
    { id: 'e5', source: 'playwright/docs/intro.md', target: 'playwright/docs/codegen.md', type: 'references', weight: 1 },
    { id: 'e6', source: 'vscode/docs/setup.md', target: 'playwright/docs/intro.md', type: 'references', weight: 0.5 },
  ],
};

export const fixtureChatAnswer: ChatAnswer = {
  answer:
    '**Building Garnet from source** comes down to installing the .NET SDK and running a ' +
    'Release build from the repo root.\n\n' +
    '### Prerequisites\n' +
    '- The **.NET 8 SDK** (the current `garnet/docs/build.md` targets .NET 8 — an older ' +
    '`build-legacy.md` still says .NET 6 and conflicts with it).\n' +
    '- A clone of the repository and a terminal at its root.\n\n' +
    '### Steps\n' +
    '1. Clone the repo and `cd` into it.\n' +
    '2. Restore dependencies: `dotnet restore`.\n' +
    '3. Build in Release configuration:\n\n' +
    '```bash\n' +
    'dotnet build -c Release\n' +
    '```\n\n' +
    '4. (Optional) Run the test suite with `dotnet test -c Release` to verify the build.\n\n' +
    '### Notes\n' +
    'The canonical instructions live in `garnet/docs/build.md`. If you hit SDK-version errors, ' +
    'check that you are on .NET 8 — the stale `build-legacy.md` page is a known conflicting ' +
    'source and is flagged for review.',
  scope: 'garnet',
  confidence: 0.82,
  needsHumanReview: false,
  citations: [
    {
      docId: 'garnet/docs/build.md',
      lineRange: [12, 24],
      commitSha: '4e44e3e9a1b2c3d4e5f60718293a4b5c6d7e8f90',
      relevance: 0.91,
      chunkId: 'garnet/docs/build.md#1',
      text: 'Build with `dotnet build -c Release` using the .NET 8 SDK.',
    },
    {
      docId: 'garnet/README.md',
      lineRange: [40, 52],
      commitSha: '6104587aa0b1c2d3e4f5061728394a5b6c7d8e9f',
      relevance: 0.68,
      chunkId: 'garnet/README.md#3',
      text: 'See docs/build.md for full build instructions.',
    },
  ],
};

export const fixtureProposal: AgentProposal = {
  proposalId: 'prop_demo01',
  action: 'merge',
  targetDocId: 'garnet/docs/build.md',
  sourceDocIds: ['garnet/docs/build.md', 'garnet/docs/build-legacy.md'],
  draft:
    '# Building Garnet\n\n' +
    '> Canonical build guide. Supersedes `build-legacy.md`.\n\n' +
    '## Prerequisites\n- .NET 8 SDK\n\n' +
    '## Build\n```bash\ndotnet build -c Release\n```\n\n' +
    '## Run the tests\n```bash\ndotnet test\n```\n',
  diff: {
    before: '## Build\nRequires the .NET 6 SDK.\n\n```bash\ndotnet build\n```\n',
    after: '## Build\nRequires the .NET 8 SDK.\n\n```bash\ndotnet build -c Release\n```\n',
    format: 'unified',
    lineRange: [10, 18],
  },
  citations: [
    {
      docId: 'garnet/docs/build.md',
      lineRange: [12, 24],
      commitSha: '4e44e3e9a1b2c3d4e5f60718293a4b5c6d7e8f90',
      relevance: 0.91,
      chunkId: 'garnet/docs/build.md#1',
      text: 'Build with `dotnet build -c Release` using the .NET 8 SDK.',
    },
  ],
  evidence: [
    {
      docId: 'garnet/docs/build-legacy.md',
      chunkId: 'garnet/docs/build-legacy.md#2',
      commitSha: '9acb2a3bb1c2d3e4f50617283940a5b6c7d8e9f0',
      lineRange: [8, 16],
      quote: 'Requires the .NET 6 SDK.',
      relevance: 0.86,
    },
  ],
  confidence: 0.79,
  riskLevel: 'medium',
  conflictsWith: ['garnet/docs/build-legacy.md'],
  verification: null,
  recommendation: 'needs-review',
  guardianReasoning:
    'The merge correctly promotes the .NET 8 instructions, but build-legacy.md is ' +
    'linked from external docs. Confirm no inbound links break before deprecating it.',
  uncertainty: 'Inbound references to build-legacy.md were not fully checked.',
  proposedBy: 'curator-agent',
  createdAt: '2026-06-24T09:00:00Z',
};

export const fixtureMetrics: MetricsDTO = {
  staleDetected: 12,
  staleFixed: 8,
  brokenLinksResolved: 5,
  conflictsDetected: 6,
  conflictsResolved: 4,
  duplicatesRemoved: 9,
  docsWithVerificationStamp: 21,
};

export const fixtureTree: TreeNode[] = [
  {
    name: 'garnet',
    type: 'directory',
    path: 'garnet',
    children: [
      { name: 'README.md', type: 'file', path: 'garnet/README.md' },
      {
        name: 'docs',
        type: 'directory',
        path: 'garnet/docs',
        children: [
          { name: 'build.md', type: 'file', path: 'garnet/docs/build.md' },
          { name: 'build-legacy.md', type: 'file', path: 'garnet/docs/build-legacy.md' },
        ],
      },
    ],
  },
  {
    name: 'playwright',
    type: 'directory',
    path: 'playwright',
    children: [
      {
        name: 'docs',
        type: 'directory',
        path: 'playwright/docs',
        children: [
          { name: 'intro.md', type: 'file', path: 'playwright/docs/intro.md' },
          { name: 'codegen.md', type: 'file', path: 'playwright/docs/codegen.md' },
        ],
      },
    ],
  },
  {
    name: 'onnxruntime',
    type: 'directory',
    path: 'onnxruntime',
    children: [
      {
        name: 'docs',
        type: 'directory',
        path: 'onnxruntime/docs',
        children: [
          { name: 'install.md', type: 'file', path: 'onnxruntime/docs/install.md' },
          { name: 'install-old.md', type: 'file', path: 'onnxruntime/docs/install-old.md' },
        ],
      },
    ],
  },
  {
    name: 'vscode',
    type: 'directory',
    path: 'vscode',
    children: [
      {
        name: 'docs',
        type: 'directory',
        path: 'vscode/docs',
        children: [{ name: 'setup.md', type: 'file', path: 'vscode/docs/setup.md' }],
      },
    ],
  },
];

// --------------------------------------------------------------------------- //
// Analysis / Insights fixtures (offline mode for the Insights surfaces).
// Numbers are kept consistent with the planted stale/duplicate/conflict
// narrative above and with `fixtureGraph`'s per-node overlay fields:
//   - garnet/docs/build-legacy.md  -> worst quality, broken links, stale, orphan
//   - onnxruntime/docs/install-old.md -> deprecated duplicate, orphan
//   - garnet/README.md             -> healthy hub (top centrality)
// Aggregate counts reconcile across the three fixtures (e.g. broken links = 4,
// orphans = 2, at-risk = 3) so the dashboards line up.
// --------------------------------------------------------------------------- //
export const fixtureAnalysisReport: AnalysisReport = {
  repoFilter: null,
  totalDocs: 12,
  qualityAvg: 0.68,
  brokenLinksDetected: 4,
  orphanCount: 2,
  atRiskCount: 3,
  worstQuality: [
    {
      docId: 'garnet/docs/build-legacy.md',
      score: 0.34,
      reasons: [
        'References the superseded .NET 6 SDK',
        'Missing "Usage" and "Troubleshooting" sections',
        'Contains 3 TODO/TBD placeholders',
      ],
    },
    {
      docId: 'onnxruntime/docs/install-old.md',
      score: 0.41,
      reasons: ['94% duplicate of install.md', 'Marked deprecated', 'Thin content (240 words)'],
    },
    {
      docId: 'playwright/docs/codegen.md',
      score: 0.6,
      reasons: ['No "Overview" heading', 'Few code examples for an API-heavy topic'],
    },
  ],
  mostAtRisk: [
    {
      docId: 'garnet/docs/build-legacy.md',
      score: 0.88,
      reasons: [
        'High-importance topic unverified for 412 days',
        'Conflicts with canonical build.md',
        'References superseded .NET 6 SDK',
      ],
    },
    {
      docId: 'onnxruntime/docs/install-old.md',
      score: 0.6,
      reasons: ['Deprecated duplicate of install.md', 'Unverified for 305 days'],
    },
    {
      docId: 'garnet/docs/build.md',
      score: 0.42,
      reasons: ['Pending merge proposal with build-legacy.md', 'Yellow health'],
    },
  ],
  topCentral: [
    { docId: 'garnet/README.md', score: 0.92, reasons: ['Repo entry point', 'Five inbound references'] },
    { docId: 'playwright/docs/intro.md', score: 0.74, reasons: ['Hub for the Playwright docs set'] },
    {
      docId: 'onnxruntime/docs/install.md',
      score: 0.66,
      reasons: ['Referenced by multiple install guides'],
    },
  ],
  asOf: '2026-06-24T21:00:00Z',
};

/**
 * Per-doc analysis keyed by `docId`. Covers a healthy hub, a decent canonical
 * doc, the known-bad stale/conflict doc, and the deprecated orphan — each
 * consistent with that node's `fixtureGraph` overlay fields. `llm` is null
 * (the opt-in notes are only fetched on demand via `getDocAnalysis(id, { llm:true })`).
 */
export const fixtureDocAnalysis: Record<string, DocAnalysis> = {
  'garnet/README.md': {
    docId: 'garnet/README.md',
    quality: {
      qualityScore: 0.88,
      readability: 64,
      gradeLevel: 8.1,
      completenessScore: 0.92,
      structureScore: 0.9,
      wordCount: 820,
      placeholderCount: 0,
      issues: [],
    },
    links: { brokenInternal: [], brokenLinkCount: 0, externalCount: 5, orphan: false, deadEnd: false },
    drift: { ageDays: 21, isStale: false, riskScore: 0.12, riskReasons: [] },
    centrality: 0.92,
    llm: null,
  },
  'garnet/docs/build.md': {
    docId: 'garnet/docs/build.md',
    quality: {
      qualityScore: 0.66,
      readability: 58,
      gradeLevel: 9.5,
      completenessScore: 0.7,
      structureScore: 0.72,
      wordCount: 540,
      placeholderCount: 0,
      issues: ['Missing a "Troubleshooting" section'],
    },
    links: {
      brokenInternal: ['./advanced-tuning.md'],
      brokenLinkCount: 1,
      externalCount: 3,
      orphan: false,
      deadEnd: false,
    },
    drift: {
      ageDays: 96,
      isStale: false,
      riskScore: 0.42,
      riskReasons: ['Pending merge proposal with build-legacy.md'],
    },
    centrality: 0.45,
    llm: null,
  },
  'garnet/docs/build-legacy.md': {
    docId: 'garnet/docs/build-legacy.md',
    quality: {
      qualityScore: 0.34,
      readability: 42.5,
      gradeLevel: 13.2,
      completenessScore: 0.4,
      structureScore: 0.45,
      wordCount: 180,
      placeholderCount: 3,
      issues: [
        'References the superseded .NET 6 SDK',
        'Missing "Usage" and "Troubleshooting" sections',
        'Contains 3 TODO/TBD placeholders',
        'Document is thin (180 words)',
      ],
    },
    links: {
      brokenInternal: ['../setup/dotnet6.md', './ci/legacy-pipeline.md'],
      brokenLinkCount: 2,
      externalCount: 1,
      orphan: true,
      deadEnd: true,
    },
    drift: {
      ageDays: 412,
      isStale: true,
      riskScore: 0.88,
      riskReasons: [
        'High-importance topic unverified for 412 days',
        'Conflicts with canonical build.md',
        'References superseded .NET 6 SDK',
      ],
    },
    centrality: 0.08,
    llm: null,
  },
  'onnxruntime/docs/install-old.md': {
    docId: 'onnxruntime/docs/install-old.md',
    quality: {
      qualityScore: 0.41,
      readability: 51,
      gradeLevel: 11,
      completenessScore: 0.5,
      structureScore: 0.55,
      wordCount: 240,
      placeholderCount: 1,
      issues: ['94% duplicate of install.md', 'Marked deprecated', 'Contains 1 placeholder'],
    },
    links: {
      brokenInternal: ['./gpu/cuda-10.md'],
      brokenLinkCount: 1,
      externalCount: 0,
      orphan: true,
      deadEnd: false,
    },
    drift: {
      ageDays: 305,
      isStale: true,
      riskScore: 0.6,
      riskReasons: ['Deprecated duplicate of install.md', 'Unverified for 305 days'],
    },
    centrality: 0.05,
    llm: null,
  },
};

export const fixtureTrends: TrendsDTO = {
  // ~2 weeks of daily snapshots: detection ramps up first, then fixes catch up
  // (the detected/fixed gap narrows) while broken links fall and quality climbs.
  // The final day matches `fixtureMetrics` (staleDetected 12, staleFixed 8,
  // conflictsDetected 6, conflictsResolved 4) and `fixtureAnalysisReport.qualityAvg`.
  series: [
    { date: '2026-06-11', staleDetected: 2, staleFixed: 0, conflictsDetected: 1, conflictsResolved: 0, brokenLinks: 11, qualityAvg: 0.56 },
    { date: '2026-06-12', staleDetected: 3, staleFixed: 0, conflictsDetected: 1, conflictsResolved: 0, brokenLinks: 11, qualityAvg: 0.57 },
    { date: '2026-06-13', staleDetected: 5, staleFixed: 1, conflictsDetected: 2, conflictsResolved: 0, brokenLinks: 10, qualityAvg: 0.58 },
    { date: '2026-06-14', staleDetected: 6, staleFixed: 1, conflictsDetected: 2, conflictsResolved: 1, brokenLinks: 10, qualityAvg: 0.59 },
    { date: '2026-06-15', staleDetected: 8, staleFixed: 2, conflictsDetected: 3, conflictsResolved: 1, brokenLinks: 9, qualityAvg: 0.6 },
    { date: '2026-06-16', staleDetected: 9, staleFixed: 3, conflictsDetected: 3, conflictsResolved: 1, brokenLinks: 9, qualityAvg: 0.61 },
    { date: '2026-06-17', staleDetected: 10, staleFixed: 4, conflictsDetected: 4, conflictsResolved: 2, brokenLinks: 8, qualityAvg: 0.62 },
    { date: '2026-06-18', staleDetected: 11, staleFixed: 5, conflictsDetected: 4, conflictsResolved: 2, brokenLinks: 7, qualityAvg: 0.63 },
    { date: '2026-06-19', staleDetected: 11, staleFixed: 5, conflictsDetected: 5, conflictsResolved: 2, brokenLinks: 6, qualityAvg: 0.64 },
    { date: '2026-06-20', staleDetected: 11, staleFixed: 6, conflictsDetected: 5, conflictsResolved: 3, brokenLinks: 6, qualityAvg: 0.65 },
    { date: '2026-06-21', staleDetected: 12, staleFixed: 6, conflictsDetected: 5, conflictsResolved: 3, brokenLinks: 5, qualityAvg: 0.66 },
    { date: '2026-06-22', staleDetected: 12, staleFixed: 7, conflictsDetected: 6, conflictsResolved: 3, brokenLinks: 4, qualityAvg: 0.67 },
    { date: '2026-06-23', staleDetected: 12, staleFixed: 8, conflictsDetected: 6, conflictsResolved: 4, brokenLinks: 4, qualityAvg: 0.675 },
    { date: '2026-06-24', staleDetected: 12, staleFixed: 8, conflictsDetected: 6, conflictsResolved: 4, brokenLinks: 3, qualityAvg: 0.68 },
  ],
  // Per-repo totals sum to the corpus aggregates in fixtureAnalysisReport
  // (totalDocs 12, brokenLinks 4, atRisk 3). The graph above visualizes a subset.
  byRepo: [
    { repo: 'garnet', totalDocs: 4, qualityAvg: 0.64, brokenLinks: 3, atRisk: 2 },
    { repo: 'playwright', totalDocs: 3, qualityAvg: 0.74, brokenLinks: 0, atRisk: 0 },
    { repo: 'onnxruntime', totalDocs: 3, qualityAvg: 0.6, brokenLinks: 1, atRisk: 1 },
    { repo: 'vscode', totalDocs: 2, qualityAvg: 0.8, brokenLinks: 0, atRisk: 0 },
  ],
  proposalAcceptanceRate: 0.72,
  confidenceHistogram: [
    { bucket: '0.0-0.2', count: 1 },
    { bucket: '0.2-0.4', count: 3 },
    { bucket: '0.4-0.6', count: 7 },
    { bucket: '0.6-0.8', count: 14 },
    { bucket: '0.8-1.0', count: 9 },
  ],
  evidenceCoverage: 0.86,
  asOf: '2026-06-24T21:00:00Z',
};
