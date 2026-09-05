'use client';

import type { Source, Trace } from '@/lib/types';
import { Tag } from '@/components/primitives';

export type StageKey = 'query' | 'cache' | 'retrieve' | 'rerank' | 'graph' | 'llm' | 'answer';

const STAGES: { key: StageKey; label: string }[] = [
  { key: 'query', label: 'Query' },
  { key: 'cache', label: 'Cache' },
  { key: 'retrieve', label: 'Hybrid Retrieval' },
  { key: 'rerank', label: 'Rerank' },
  { key: 'graph', label: 'Graph' },
  { key: 'llm', label: 'LLM' },
  { key: 'answer', label: 'Answer' },
];

/**
 * PipelineRow — the signature element: an amber signal trace through the
 * retrieval pipeline. `active` lights one stage; `doneThrough` marks every
 * stage up to and including it as complete. Timings render from the trace
 * object once the backend metadata arrives.
 */
export function PipelineRow({
  trace,
  active,
  doneThrough,
}: {
  trace?: Trace;
  active?: StageKey;
  doneThrough?: StageKey;
}) {
  const t = trace || {};
  const model = String(t.model ?? '')
    .replace('nvidia/', '')
    .replace('meta/', '')
    .split(' /')[0];

  const labels: Record<StageKey, string> = {
    query: 'Query',
    cache: t.cache === 'hit' ? 'Cache HIT' : 'Cache miss',
    retrieve: t.hybrid ? 'Hybrid Retrieve' : 'Vector only',
    rerank: t.reranker ? 'Rerank' : 'No rerank',
    graph: `Graph ${Number(t.graph_entities ?? 0)} entities`,
    llm: `LLM ${model || 'fallback'}`,
    answer: `Answer ${Math.round(Number(t.latency_ms ?? 0))} ms`,
  };

  const kind = (key: StageKey): 'done' | 'hit' | 'warn' | 'active' => {
    if (active === key) return 'active';
    if (key === 'cache' && t.cache === 'hit') return 'hit';
    if (key === 'retrieve' && !t.hybrid) return 'warn';
    if (key === 'rerank' && !t.reranker) return 'warn';
    if (key === 'graph' && !t.graph_entities) return 'warn';
    if (key === 'llm' && !t.model) return 'warn';
    return 'done';
  };

  const cls = (key: StageKey) => {
    if (active === key) return 'pstage active';
    // Stages beyond `doneThrough` haven't run yet — keep them neutral.
    if (doneThrough && STAGES.findIndex((s) => s.key === doneThrough) < STAGES.findIndex((s) => s.key === key)) {
      return 'pstage';
    }
    if (kind(key) === 'hit') return 'pstage hit';
    if (kind(key) === 'warn') return 'pstage warn';
    return 'pstage done';
  };

  return (
    <div className="pipeline-stages">
      {STAGES.map((s, i) => (
        <span key={s.key} style={{ display: 'contents' }}>
          {i > 0 && <span className="parrow">→</span>}
          <span className={cls(s.key)}>{labels[s.key]}</span>
        </span>
      ))}
      <div className="trace-line" style={{ width: '100%' }} />
    </div>
  );
}

export function StatChips({ trace }: { trace?: Trace }) {
  const t = trace || {};
  const chips: string[] = [];
  if (t.candidates != null) chips.push(`candidates: ${t.candidates}`);
  if (t.chunks_used != null) chips.push(`chunks used: ${t.chunks_used}`);
  if (t.graph_entities != null) chips.push(`graph entities: ${t.graph_entities}`);
  if (t.graph_relations != null) chips.push(`graph relations: ${t.graph_relations}`);
  if (t.complexity != null) chips.push(`complexity: ${t.complexity ? 'complex' : 'simple'}`);
  if (t.thinking != null) chips.push(`thinking: ${t.thinking ? 'on' : 'off'}`);
  if (t.routing_mode) chips.push(`router: ${t.routing_mode}`);
  if (chips.length === 0) return null;
  return (
    <div className="stat-chips">
      {chips.map((c) => (
        <span key={c} className="stat-chip">{c}</span>
      ))}
    </div>
  );
}

export default function EvidenceTrace({
  trace,
  sources,
  active,
  doneThrough,
}: {
  trace?: Trace;
  sources?: Source[];
  active?: StageKey;
  doneThrough?: StageKey;
}) {
  if ((!sources || sources.length === 0) && !trace) return null;
  const n = sources?.length ?? 0;
  return (
    <details className="expander" open>
      <summary>🔍 Why this answer? — {n} source(s)</summary>
      <div className="expander-body">
        {trace && (
          <>
            <PipelineRow trace={trace} active={active} doneThrough={doneThrough} />
            <StatChips trace={trace} />
          </>
        )}
        {(sources ?? []).map((s, i) => (
          <div className="citation" key={`${s.doc_id ?? 'src'}-${i}`}>
            <div className="cite-header">
              <Tag tone="cyan">[{i + 1}]</Tag>{' '}
              {s.citation || s.doc_id || 'Unknown'}
              <span style={{ color: 'var(--text-dim)' }}>
                {' '}
                | distance: {typeof s.distance === 'number' ? s.distance.toFixed(3) : '—'}
              </span>
            </div>
            <div className="cite-text">{s.excerpt ? `${s.excerpt}…` : ''}</div>
          </div>
        ))}
      </div>
    </details>
  );
}
