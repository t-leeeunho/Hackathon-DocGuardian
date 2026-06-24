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
  ChatAnswer,
  DocumentIntakeResponse,
  DocumentResponse,
  GraphDTO,
  GraphEdge,
  TreeNode,
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
      Array<{ name: string; type: string; path: string; children?: unknown[] }>
    >(`/tree${qs}`);
    return normalizeTree(raw);
  },

  getDocument(docId: string): Promise<DocumentResponse> {
    return request<DocumentResponse>(`/documents/${encodeURIComponent(docId)}`);
  },

  ingestDocument(content: string, name?: string): Promise<DocumentIntakeResponse> {
    return request<DocumentIntakeResponse>('/documents', {
      method: 'POST',
      body: JSON.stringify({ name: name ?? 'untitled.md', content, namespace: 'user' }),
    });
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
};

function normalizeTree(
  nodes: Array<{ name: string; type: string; path: string; children?: unknown[] }>,
): TreeNode[] {
  return nodes.map((n) => ({
    name: n.name,
    type: n.type === 'file' ? 'file' : 'directory',
    path: n.path,
    children: n.children
      ? normalizeTree(
          n.children as Array<{ name: string; type: string; path: string; children?: unknown[] }>,
        )
      : undefined,
  }));
}
