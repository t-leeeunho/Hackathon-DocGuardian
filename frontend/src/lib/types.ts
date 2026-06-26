/**
 * DocGuardian frontend data contracts.
 *
 * These TypeScript interfaces mirror the **camelCase** HTTP API documented in
 * README §8B and produced by the backend response DTOs (`backend/app/main.py`)
 * and camelCase dicts (`backend/app/storage/queries.py`). The agent endpoints
 * (`/chat`, `/propose`) emit snake_case; the API client in `./api.ts` converts
 * those to the camelCase shapes below before they reach components.
 */

// --------------------------------------------------------------------------- //
// Graph (GET /graph)
// --------------------------------------------------------------------------- //
export type NodeHealth = 'green' | 'yellow' | 'red' | 'gray';

export type GraphEdgeType =
  | 'references'
  | 'duplicate-of'
  | 'conflicts-with'
  | 'deprecated-by'
  | 'related-to'
  | 'sibling';

export interface GraphNode {
  id: string;
  label: string;
  health: NodeHealth;
  /** Normalized 0–1 size used to scale the node. */
  size: number;
  accessible: boolean;
  repo: string;
  /** Analysis (Insights) overlay — additive, optional. */
  qualityScore?: number;
  brokenLinkCount?: number;
  orphan?: boolean;
  /** 0–1 PageRank centrality (drives size when present). */
  centrality?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  weight?: number;
}

export interface GraphDTO {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// --------------------------------------------------------------------------- //
// File tree (GET /tree)
// --------------------------------------------------------------------------- //
export interface TreeNode {
  name: string;
  type: 'directory' | 'file';
  path: string;
  summary?: string;
  children?: TreeNode[];
}

// --------------------------------------------------------------------------- //
// Documents (GET /documents/{id}, POST /documents)
// --------------------------------------------------------------------------- //
export interface ChunkDetail {
  chunkId: string;
  headingPath: string[];
  lineRange: [number, number];
  text: string;
  tokenCount?: number;
}

export interface DocumentResponse {
  docId: string;
  repo: string;
  path: string;
  commitSha: string;
  commitDate?: string;
  /** Librarian-assigned title (drop-off docs that were rewritten). */
  title?: string | null;
  /** True when this doc is the AI-agent-friendly rewrite of a user drop-off. */
  aiRewritten?: boolean;
  /** Path the user originally dropped the file at, before re-placement. */
  originalPath?: string | null;
  /** Why the agent rewrote + filed it here. */
  rationale?: string | null;
  chunks: ChunkDetail[];
}

/** Original drop-off vs. the AI rewrite (GET /original/{id}). */
export interface DocumentSource {
  docId: string;
  path: string;
  title?: string | null;
  summary?: string | null;
  aiRewritten: boolean;
  rationale?: string | null;
  originalPath?: string | null;
  /** The user's untouched original document. */
  originalContent: string;
  /** The AI-agent-friendly rewrite shown by default. */
  aiContent: string;
}

export interface DocumentIntakeResponse {
  docId: string;
  chunks: number;
  edges: number;
  conflictEdges?: number;
  summary?: string;
  /** Librarian-assigned title. */
  title?: string | null;
  /** Library category the agent filed the doc under. */
  category?: string | null;
  /** Why the agent rewrote + placed it here. */
  rationale?: string | null;
  /** Path the user dropped the file at. */
  originalPath?: string | null;
  /** Namespace-relative path the agent chose. */
  suggestedPath?: string | null;
  /** True when the stored content is an AI rewrite of the original. */
  aiRewritten?: boolean;
}

export type JobStatus = 'queued' | 'processing' | 'succeeded' | 'failed';

/** One page imported from a website crawl (POST /ingest/url). */
export interface UrlImportedDoc {
  url: string;
  title: string;
  docId: string;
  chunks: number;
}

/** Result of a website import (POST /ingest/url → job.result). */
export interface UrlIngestResult {
  startUrl: string;
  namespace: string;
  pagesFound: number;
  imported: number;
  docs: UrlImportedDoc[];
  errors?: { url: string; error: string }[];
}

export interface IngestJob {
  jobId: string;
  docId: string;
  status: JobStatus;
  result?: DocumentIntakeResponse | UrlIngestResult | null;
  error?: string | null;
  createdAt?: number;
  updatedAt?: number;
  /** Live progress for multi-page (URL) imports. */
  message?: string;
  imported?: number;
}

/** A tiny event envelope from `WS /stream`. */
export interface StreamEvent {
  type: 'connected' | 'heartbeat' | 'ingest' | 'graph' | 'metrics' | 'proposal';
  jobId?: string;
  docId?: string;
  status?: string;
  error?: string;
  [k: string]: unknown;
}

// --------------------------------------------------------------------------- //
// Agents (POST /chat, POST /propose)
// --------------------------------------------------------------------------- //
export interface Citation {
  docId: string;
  lineRange?: [number, number];
  commitSha: string;
  relevance: number;
  chunkId?: string;
  text?: string;
}

export interface ChatAnswer {
  answer: string;
  scope?: string;
  reasoning?: string;
  citations: Citation[];
  confidence: number;
  needsHumanReview: boolean;
}

export type ProposalAction =
  | 'create'
  | 'update'
  | 'merge'
  | 'link'
  | 'deprecate'
  | 'flag';

export type RiskLevel = 'low' | 'medium' | 'high';

export type Recommendation = 'approve' | 'needs-review' | 'reject';

export interface Evidence {
  chunkId?: string;
  docId: string;
  commitSha?: string;
  lineRange?: [number, number];
  quote?: string;
  relevance?: number;
}

export interface ProposalDiff {
  before: string;
  after: string;
  format?: 'unified' | 'side-by-side';
  lineRange?: [number, number] | null;
}

export interface Verification {
  sandboxRun: boolean;
  passed?: boolean | null;
  command?: string | null;
  commitSha?: string | null;
  durationMs?: number | null;
}

export interface AgentProposal {
  proposalId?: string | null;
  action: ProposalAction;
  targetDocId?: string | null;
  sourceDocIds?: string[];
  diff?: ProposalDiff | null;
  draft: string;
  citations: Citation[];
  evidence?: Evidence[];
  confidence: number;
  riskLevel: RiskLevel;
  conflictsWith?: string[];
  verification?: Verification | null;
  recommendation?: Recommendation | null;
  guardianReasoning?: string | null;
  uncertainty?: string | null;
  proposedBy?: string;
  createdAt?: string | null;
}

// --------------------------------------------------------------------------- //
// Metrics (GET /metrics — not yet implemented; demo via fixtures)
// --------------------------------------------------------------------------- //
export interface MetricsDTO {
  staleDetected: number;
  staleFixed: number;
  brokenLinksResolved: number;
  conflictsDetected: number;
  conflictsResolved: number;
  duplicatesRemoved: number;
  docsWithVerificationStamp: number;
}

// --------------------------------------------------------------------------- //
// Analysis / Insights (GET /analysis, /analysis/{docId}, /analysis/trends)
// Deterministic-first; `llm` is populated only on demand (?llm=true).
// --------------------------------------------------------------------------- //
export interface DocQuality {
  /** 0–1 composite quality score. */
  qualityScore: number;
  /** Flesch reading-ease score. */
  readability: number;
  /** Flesch–Kincaid grade level. */
  gradeLevel: number;
  /** 0–1 expected-section coverage. */
  completenessScore: number;
  /** 0–1 structural quality. */
  structureScore: number;
  wordCount: number;
  placeholderCount: number;
  issues: string[];
}

export interface DocLinks {
  /** Unresolved internal link targets. */
  brokenInternal: string[];
  brokenLinkCount: number;
  externalCount: number;
  /** No inbound references. */
  orphan: boolean;
  /** No outbound references. */
  deadEnd: boolean;
}

export interface DocDrift {
  ageDays: number;
  isStale: boolean;
  /** 0–1 decay/at-risk score. */
  riskScore: number;
  riskReasons: string[];
}

export interface LlmQualityNotes {
  clarityScore: number | null;
  issues: string[];
  suggestedSections: string[];
}

export interface DocAnalysis {
  docId: string;
  quality: DocQuality;
  links: DocLinks;
  drift: DocDrift;
  /** 0–1 PageRank centrality. */
  centrality: number;
  /** Opt-in LLM notes (only when requested with ?llm=true). */
  llm?: LlmQualityNotes | null;
}

/** A doc reference with a score + reasons, reused across report lists. */
export interface DocRef {
  docId: string;
  score: number;
  reasons: string[];
}

export interface AnalysisReport {
  repoFilter?: string | null;
  totalDocs: number;
  qualityAvg: number;
  brokenLinksDetected: number;
  orphanCount: number;
  atRiskCount: number;
  worstQuality: DocRef[];
  mostAtRisk: DocRef[];
  topCentral: DocRef[];
  asOf: string;
}

export interface TrendPoint {
  date: string;
  staleDetected: number;
  staleFixed: number;
  conflictsDetected: number;
  conflictsResolved: number;
  brokenLinks: number;
  qualityAvg: number;
}

export interface RepoBreakdown {
  repo: string;
  totalDocs: number;
  qualityAvg: number;
  brokenLinks: number;
  atRisk: number;
}

export interface HistogramBucket {
  bucket: string;
  count: number;
}

export interface TrendsDTO {
  series: TrendPoint[];
  byRepo: RepoBreakdown[];
  proposalAcceptanceRate: number;
  confidenceHistogram: HistogramBucket[];
  evidenceCoverage: number;
  asOf: string;
}

// --------------------------------------------------------------------------- //
// UI events (client-side only)
// --------------------------------------------------------------------------- //
export interface GraphHighlightEvent {
  reason: 'chat-evidence' | 'proposal-evidence' | 'conflict' | 'duplicate' | 'manual';
  nodeIds: string[];
  edgeIds?: string[];
  /** Highlight strength in [0,1], typically the top citation relevance. */
  intensity: number;
  /** How long the highlight stays before auto-clearing, in ms. */
  ttlMs: number;
  /** When true, the graph also flies the camera to the highlighted node(s). */
  focus?: boolean;
}
