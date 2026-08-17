// ── Typed API client for the Synapse FastAPI backend ──────────────────────
import type {
  BenchmarkResponse, DebugSearchResponse, DocumentDetail, DocumentMeta,
  EntitiesResponse, FeedbackResponse, GraphNodeDetail, GraphPathResponse,
  GraphResponse, Health, IngestInitializeResponse, IngestUploadResponse,
  LlmStatus, QueryResponse, StreamEvent,
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

export const api = {
  health: (signal?: AbortSignal) => get<Health>('/health', signal),
  llmStatus: (signal?: AbortSignal) => get<LlmStatus>('/llm/status', signal),
  entities: (signal?: AbortSignal) => get<EntitiesResponse>('/entities', signal),
  documents: (signal?: AbortSignal) => get<DocumentMeta[]>('/documents', signal),
  document: (docId: string) => get<DocumentDetail>(`/documents/${encodeURIComponent(docId)}`),
  graph: (maxNodes = 200) => get<GraphResponse>(`/graph?max_nodes=${maxNodes}`),
  graphNode: (id: string) => get<GraphNodeDetail>(`/graph/node/${encodeURIComponent(id)}`),
  graphPath: (source: string, target: string) =>
    get<GraphPathResponse>(`/graph/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`),
  debugSearch: (q: string, n = 5) =>
    get<DebugSearchResponse>(`/debug/search?q=${encodeURIComponent(q)}&n=${n}`),

  query: (question: string, topK = 5, routingMode = 'auto', signal?: AbortSignal) =>
    post<QueryResponse>('/query', { question, top_k: topK, routing_mode: routingMode }),

  benchmark: (maxQuestions = 40) =>
    get<BenchmarkResponse>(`/benchmark/run?max_questions=${maxQuestions}`),

  ingestInitialize: () => post<IngestInitializeResponse>('/ingest/initialize'),

  ingestUpload: (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    return post<IngestUploadResponse>('/ingest/upload', form);
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
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ question, top_k: topK, routing_mode: routingMode }),
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
