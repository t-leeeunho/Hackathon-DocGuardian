/**
 * DocGuardian API client.
 *
 * Thin typed wrapper over the backend (README §8B). Most endpoints already
 * return camelCase; this client normalizes the few that don't:
 *   - `/graph` edges use `from`/`to`  -> mapped to `source`/`target` (+ a synthetic id).
 *   - `/tree` uses `type: 'folder'`   -> mapped to `'directory'` for the UI.
 *   - `/chat` & `/propose` emit snake_case -> deep-converted to camelCase.
 *
 * When the backend is unreachable (or Azure is unconfigured for the agents),
 * callers fall back to the demo fixtures; this client just surfaces `ApiError`.
 */
import type {
  AgentProposal,
  AnalysisReport,
  ChatAnswer,
  DocAnalysis,
  DocumentIntakeResponse,
  DocumentResponse,
  DocumentSource,
  GraphDTO,
  GraphEdge,
  IngestJob,
  TreeNode,
  TrendsDTO,
} from './types';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

type Json = Record<string, unknown>;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
  } catch (err) {
    // Network failure / backend down -> status 0 signals offline to callers.
    throw new ApiError(0, err instanceof Error ? err.message : 'Network error');
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body — keep statusText */
    }
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as T;
}

// --------------------------------------------------------------------------- //
// snake_case -> camelCase (for the agent endpoints)
// --------------------------------------------------------------------------- //
function toCamel(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
}

function camelize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(camelize);
  if (value !== null && typeof value === 'object') {
    const out: Json = {};
    for (const [k, v] of Object.entries(value as Json)) {
      out[toCamel(k)] = camelize(v);
    }
    return out;
  }
  return value;
}

// --------------------------------------------------------------------------- //
// Endpoint methods
// --------------------------------------------------------------------------- //
export const api = {
  async getGraph(repo?: string): Promise<GraphDTO> {
    const qs = repo ? `?repo=${encodeURIComponent(repo)}` : '';
    const raw = await request<{
      nodes: GraphDTO['nodes'];
      edges: Array<{ from: string; to: string; type: string; weight?: number }>;
    }>(`/graph${qs}`);
    const edges: GraphEdge[] = raw.edges.map((e, i) => ({
      id: `${e.from}->${e.to}:${e.type}:${i}`,
      source: e.from,
      target: e.to,
      type: e.type as GraphEdge['type'],
      weight: e.weight,
    }));
    return { nodes: raw.nodes, edges };
  },

  async getTree(namespace?: string): Promise<TreeNode[]> {
    const qs = namespace ? `?namespace=${encodeURIComponent(namespace)}` : '';
    const raw = await request<
      Array<{ name: string; type: string; path: string; summary?: string; children?: unknown[] }>
    >(`/tree${qs}`);
    return normalizeTree(raw);
  },

  getDocument(docId: string): Promise<DocumentResponse> {
    return request<DocumentResponse>(`/documents/${encodeURIComponent(docId)}`);
  },

  /** The original drop-off + the AI rewrite, for the "view original" toggle. */
  getDocumentSource(docId: string): Promise<DocumentSource> {
    return request<DocumentSource>(`/original/${encodeURIComponent(docId)}`);
  },

  ingestDocument(content: string, name?: string): Promise<DocumentIntakeResponse> {
    return request<DocumentIntakeResponse>('/documents', {
      method: 'POST',
      body: JSON.stringify({ name: name ?? 'untitled.md', content, namespace: 'user' }),
    });
  },

  /** Submit a document for background ingestion. Resolves immediately with a job. */
  ingestDocumentAsync(content: string, name?: string): Promise<IngestJob> {
    return request<IngestJob>('/documents?background=true', {
      method: 'POST',
      body: JSON.stringify({ name: name ?? 'untitled.md', content, namespace: 'user' }),
    });
  },

  getJob(jobId: string): Promise<IngestJob> {
    return request<IngestJob>(`/jobs/${encodeURIComponent(jobId)}`);
  },

  /** Crawl a website URL (+ sub-pages) and import them. Resolves with a job to poll. */
  ingestUrl(url: string, maxPages = 8, maxDepth = 2, namespace?: string): Promise<IngestJob> {
    return request<IngestJob>('/ingest/url', {
      method: 'POST',
      body: JSON.stringify({ url, maxPages, maxDepth, namespace }),
    });
  },

  /** ws:// URL for the live event stream (README §8B WS /stream). */
  streamUrl(): string {
    return API_BASE.replace(/^http/, 'ws') + '/stream';
  },

  async chat(query: string, repo?: string): Promise<ChatAnswer> {
    const raw = await request<Json>('/chat', {
      method: 'POST',
      body: JSON.stringify({ query, repo }),
    });
    return camelize(raw) as ChatAnswer;
  },

  async propose(targetDocId: string, instruction: string, repo?: string): Promise<AgentProposal> {
    const raw = await request<Json>('/propose', {
      method: 'POST',
      body: JSON.stringify({ instruction, repo }),
    });
    const proposal = camelize(raw) as AgentProposal;
    // The backend scopes by repo, not a single doc; keep the clicked target visible.
    if (!proposal.targetDocId) proposal.targetDocId = targetDocId;
    return proposal;
  },

  // ------------------------------------------------------------------------- //
  // Analysis / Insights (README §8B). These endpoints already emit camelCase
  // DTOs (like /graph & /documents), so no snake_case conversion is needed.
  // Like the other methods, they just surface `ApiError`; callers fall back to
  // the demo fixtures (fixtureAnalysisReport / fixtureDocAnalysis / fixtureTrends).
  // ------------------------------------------------------------------------- //
  /** Corpus-wide analysis report: aggregates + worst-offender lists (GET /analysis). */
  getAnalysis(repo?: string): Promise<AnalysisReport> {
    const qs = repo ? `?repo=${encodeURIComponent(repo)}` : '';
    return request<AnalysisReport>(`/analysis${qs}`);
  },

  /**
   * Per-doc analysis: quality + links + drift + centrality (GET /analysis/{docId}).
   * Pass `{ llm: true }` to additionally request the opt-in LLM notes.
   */
  getDocAnalysis(docId: string, opts?: { llm?: boolean }): Promise<DocAnalysis> {
    const qs = opts?.llm ? '?llm=true' : '';
    return request<DocAnalysis>(`/analysis/${encodeURIComponent(docId)}${qs}`);
  },

  /** Corpus governance/insights trends: time-series, acceptance rate, distributions (GET /analysis/trends). */
  getTrends(repo?: string): Promise<TrendsDTO> {
    const qs = repo ? `?repo=${encodeURIComponent(repo)}` : '';
    return request<TrendsDTO>(`/analysis/trends${qs}`);
  },
};

function normalizeTree(
  nodes: Array<{ name: string; type: string; path: string; summary?: string; children?: unknown[] }>,
): TreeNode[] {
  return nodes.map((n) => ({
    name: n.name,
    type: n.type === 'file' ? 'file' : 'directory',
    path: n.path,
    summary: n.summary,
    children: n.children
      ? normalizeTree(
          n.children as Array<{
            name: string;
            type: string;
            path: string;
            summary?: string;
            children?: unknown[];
          }>,
        )
      : undefined,
  }));
}
