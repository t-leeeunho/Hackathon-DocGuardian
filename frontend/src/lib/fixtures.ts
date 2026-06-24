/**
 * Demo fixtures — used when the backend is unreachable (offline/demo mode) and
 * for the governance-dependent panels (metrics, proposal review) that have no
 * live endpoint yet. They model a small, deliberately conflicted corpus so the
 * stale / duplicate / conflict story is visible without a running database.
 */
import type {
  AgentProposal,
  ChatAnswer,
  GraphDTO,
  MetricsDTO,
  TreeNode,
} from './types';

export const fixtureGraph: GraphDTO = {
  nodes: [
    { id: 'garnet/README.md', label: 'README.md', health: 'green', size: 0.9, accessible: true, repo: 'garnet' },
    { id: 'garnet/docs/build.md', label: 'build.md', health: 'yellow', size: 0.6, accessible: true, repo: 'garnet' },
    { id: 'garnet/docs/build-legacy.md', label: 'build-legacy.md', health: 'red', size: 0.5, accessible: true, repo: 'garnet' },
    { id: 'playwright/docs/intro.md', label: 'intro.md', health: 'green', size: 0.8, accessible: true, repo: 'playwright' },
    { id: 'playwright/docs/codegen.md', label: 'codegen.md', health: 'green', size: 0.55, accessible: true, repo: 'playwright' },
    { id: 'onnxruntime/docs/install.md', label: 'install.md', health: 'yellow', size: 0.7, accessible: true, repo: 'onnxruntime' },
    { id: 'onnxruntime/docs/install-old.md', label: 'install-old.md', health: 'gray', size: 0.4, accessible: false, repo: 'onnxruntime' },
    { id: 'vscode/docs/setup.md', label: 'setup.md', health: 'green', size: 0.75, accessible: true, repo: 'vscode' },
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
    'To build Garnet from source, run `dotnet build -c Release` from the repository ' +
    'root after installing the .NET 8 SDK. The canonical instructions live in ' +
    '`garnet/docs/build.md`; an older `build-legacy.md` still references .NET 6 and ' +
    'conflicts with the current guide.',
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
