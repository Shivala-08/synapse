// ── Typed API client for the Synapse FastAPI backend ──────────────────────
import type {
  BenchmarkResponse, DebugSearchResponse, DocumentDetail, DocumentMeta,
  DomainsResponse, EntitiesResponse, FeedbackResponse, GraphNodeDetail, GraphPathResponse,
  GraphResponse, Health, IngestInitializeResponse, IngestUploadResponse,
  LlmStatus, MasteryResponse, QueryResponse, ResyncResponse, RoadmapPlan, StreamEvent,
} from './types';

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { signal });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ApiError(`Cannot reach backend at ${API_URL} — is it running?`);
  }
  if (!res.ok) throw new ApiError(`HTTP ${res.status}`, res.status);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
      body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
    });
  } catch {
    throw new ApiError(`Cannot reach backend at ${API_URL} — is it running?`);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      if (j?.detail) detail = String(j.detail);
    } catch { /* ignore */ }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

// ── Endpoints ──────────────────────────────────────────────────────────────

const dq = (domainId?: string) => domainId ? `&domain_id=${encodeURIComponent(domainId)}` : '';

export const api = {
  health: (signal?: AbortSignal) => get<Health>('/health', signal),
  llmStatus: (signal?: AbortSignal) => get<LlmStatus>('/llm/status', signal),
  domains: (signal?: AbortSignal) => get<DomainsResponse>('/domains', signal),
  entities: (domainId?: string, signal?: AbortSignal) =>
    get<EntitiesResponse>(`/entities?${dq(domainId).slice(1) || '_'}`, signal),
  documents: (domainId?: string, signal?: AbortSignal) =>
    get<DocumentMeta[]>(`/documents${domainId ? `?domain_id=${encodeURIComponent(domainId)}` : ''}`, signal),
  document: (docId: string) => get<DocumentDetail>(`/documents/${encodeURIComponent(docId)}`),
  graph: (maxNodes = 200, domainId?: string) =>
    get<GraphResponse>(`/graph?max_nodes=${maxNodes}${dq(domainId)}`),
  graphNode: (id: string, domainId?: string) =>
    get<GraphNodeDetail>(`/graph/node/${encodeURIComponent(id)}${dq(domainId)}`),
  graphPath: (source: string, target: string, domainId?: string) =>
    get<GraphPathResponse>(`/graph/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}${dq(domainId)}`),
  debugSearch: (q: string, n = 5) =>
    get<DebugSearchResponse>(`/debug/search?q=${encodeURIComponent(q)}&n=${n}`),

  query: (question: string, topK = 5, routingMode = 'auto', signal?: AbortSignal, domainId?: string) =>
    post<QueryResponse>('/query', { question, top_k: topK, routing_mode: routingMode, domain_id: domainId || undefined }),

  benchmark: (maxQuestions = 40, domainId?: string) =>
    get<BenchmarkResponse>(`/benchmark/run?max_questions=${maxQuestions}${dq(domainId)}`),

  ingestInitialize: () => post<IngestInitializeResponse>('/ingest/initialize'),

  ingestUpload: (files: File[], domainId?: string) => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    const q = domainId ? `?domain_id=${encodeURIComponent(domainId)}` : '';
    return post<IngestUploadResponse>(`/ingest/upload${q}`, form);
  },

  reSync: (domainId: string) =>
    post<ResyncResponse>(`/ingest/re-sync?domain_id=${encodeURIComponent(domainId)}`),

  mastery: (domainId?: string) =>
    get<MasteryResponse>(domainId ? `/mastery?${dq(domainId).slice(1)}` : '/mastery'),

  roadmapPlan: (domainId: string, examDate: string | null, dailyHours: number) => {
    const params = new URLSearchParams({ domain_id: domainId, daily_hours: String(dailyHours) });
    if (examDate) params.set('exam_date', examDate);
    return get<RoadmapPlan>(`/roadmap/plan?${params.toString()}`);
  },

  feedback: (question: string, answer: string, score: number) =>
    post<FeedbackResponse>('/feedback', { question, answer, score }),
};

// ── SSE streaming for /query/stream ────────────────────────────────────────

export async function streamQuery(
  question: string,
  topK: number,
  routingMode: string,
  signal: AbortSignal,
  onEvent: (ev: StreamEvent) => void,
  domainId?: string,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ question, top_k: topK, routing_mode: routingMode, domain_id: domainId || undefined }),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === 'AbortError') return;
    throw new ApiError(`Cannot reach backend at ${API_URL} — is it running?`);
  }
  if (!res.ok || !res.body) {
    throw new ApiError(`HTTP ${res.status}`, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by blank lines
      let idx: number;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const dataLine = frame.split('\n').find((l) => l.startsWith('data:'));
        if (!dataLine) continue;
        const payload = dataLine.slice(5).trim();
        if (!payload) continue;
        try {
          const ev = JSON.parse(payload) as StreamEvent;
          onEvent(ev);
        } catch {
          // ignore malformed frames
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
