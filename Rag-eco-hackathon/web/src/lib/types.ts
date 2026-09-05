// ── API response types (mirror the FastAPI backend) ───────────────────────

export interface Health {
  status: string;
  version: string;
}

export interface LlmStatus {
  nvidia_available: boolean;
  ollama_available: boolean;
  model: string;
  base_url?: string;
  mode: string;
}

export interface EntityStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  density: number;
}

export interface EntitiesResponse {
  entities: Record<string, string[]>;
  stats: EntityStats;
}

export interface DocumentMeta {
  doc_id: string;
  filename: string;
  type: string;
  chunk_count: number;
  upload_date: string;
  entities_found?: number;
}

export interface DocumentChunk {
  chunk_id: string;
  text: string;
  metadata: Record<string, unknown>;
}

export interface DocumentDetail {
  doc_id: string;
  chunks: DocumentChunk[];
}

export interface GraphNode {
  id: string;
  type?: string;
  color?: string;
  size?: number;
  degree?: number;
}

export interface GraphEdge {
  from: string;
  to: string;
  relation?: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNodeDetail {
  id: string;
  type?: string;
  color?: string;
  degree?: number;
  doc_id?: string;
  neighbors: { id: string; relation?: string; type?: string }[];
  neighbor_types?: Record<string, string[]>;
  error?: string;
}

export interface GraphPathResponse {
  path?: string[];
  length?: number;
  path_nodes?: { id: string; color?: string }[];
  path_edges?: GraphEdge[];
  error?: string;
}

export interface Trace {
  cache?: string;
  hybrid?: boolean;
  reranker?: boolean;
  candidates?: number;
  chunks_used?: number;
  graph_entities?: number;
  graph_relations?: number;
  complexity?: boolean;
  thinking?: boolean;
  model?: string;
  routing_mode?: string;
  latency_ms?: number;
  [key: string]: unknown;
}

export interface Source {
  doc_id?: string;
  citation?: string;
  excerpt?: string;
  distance?: number;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  confidence: number | string;
  entities_used?: string[];
  key_points?: string[];
  model_used?: string;
  latency_ms?: number;
  trace?: Trace;
  error?: string;
}

export type StreamEventType = 'token' | 'metadata' | 'error' | 'done';

export interface StreamEvent {
  type: StreamEventType;
  content: unknown;
}

export interface BenchmarkResult {
  id: string;
  question: string;
  expected: string;
  got: string;
  passed: boolean;
  similarity?: number;
  passed_keyword?: boolean;
  latency_ms: number;
  category?: string;
  confidence?: number | string;
}

export interface BenchmarkResponse {
  total: number;
  correct: number;
  accuracy_pct: number;
  avg_latency_ms: number;
  model_used: string;
  results: BenchmarkResult[];
}

export interface DebugHit {
  rank: number;
  doc_id: string;
  score: number;
  excerpt: string;
}

export interface DebugSearchResponse {
  hits: DebugHit[];
  total_in_db: number;
}

export interface IngestStats {
  files_ingested: number;
  total_chunks: number;
}

export interface IngestInitializeResponse {
  stats: IngestStats;
}

export interface IngestUploadResult {
  doc_id?: string;
  chunk_count?: number;
  status?: string;
  error?: string;
  filename?: string;
}

export interface IngestUploadResponse {
  results: IngestUploadResult[];
}

export interface DomainInfo {
  domain_id: string;
  display_name: string;
  source_path?: string;
  collection_name?: string;
  link_syntax?: string;
}

export interface DomainsResponse {
  domains: DomainInfo[];
}

export interface FeedbackResponse {
  status?: string;
  [key: string]: unknown;
}

export interface MasterySubject {
  name: string;
  mastery_pct: number;
  total: number;
  connected: number;
  entity_ids: string[];
}

export interface MasteryResponse {
  domain_id: string;
  overall_pct: number;
  subjects: MasterySubject[];
  basis: string;
  note?: string;
}

export interface RoadmapBlock {
  subject: string;
  hours: number;
  priority: number;
  mastery_pct: number;
}

export interface RoadmapDay {
  date: string;
  weekday: string;
  day: number;
  month: string;
  blocks: RoadmapBlock[];
}

export interface RoadmapPlan {
  domain_id: string;
  exam_date: string | null;
  days_remaining: number;
  shown_days: number;
  daily_hours: number;
  subjects: { name: string; mastery_pct: number; total: number }[];
  days: RoadmapDay[];
  basis: string;
  note?: string;
}

export interface ResyncResponse {
  domain_id: string;
  source_path?: string;
  added: string[];
  skipped_count: number;
  errors: { file: string; error: string }[];
  synced_at?: string;
}
