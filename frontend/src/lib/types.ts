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
  chunks: ChunkDetail[];
}

export interface DocumentIntakeResponse {
  docId: string;
  chunks: number;
  edges: number;
  conflictEdges?: number;
  summary?: string;
}

export type JobStatus = 'queued' | 'processing' | 'succeeded' | 'failed';

export interface IngestJob {
  jobId: string;
  docId: string;
  status: JobStatus;
  result?: DocumentIntakeResponse | null;
  error?: string | null;
  createdAt?: number;
  updatedAt?: number;
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
