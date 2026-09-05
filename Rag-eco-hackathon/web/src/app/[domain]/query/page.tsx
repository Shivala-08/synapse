'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { CircleNotch, X, Prohibit } from '@phosphor-icons/react';
import EvidenceTrace, { PipelineRow, StatChips, type StageKey } from '@/components/EvidenceTrace';
import { Tag } from '@/components/primitives';
import SignalPulse from '@/components/SignalPulse';
import { ApiError, streamQuery } from '@/lib/api';
import { useDomain } from '@/lib/DomainContext';
import type { QueryResponse, Source, Trace } from '@/lib/types';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  question?: string;
  confidence?: number | string;
  modelUsed?: string;
  latencyMs?: number;
  entities?: string[];
  keyPoints?: string[];
  sources?: Source[];
  trace?: Trace;
}

const EXAMPLES: { label: string; question: string }[] = [
  {
    label: 'Overview',
    question: 'Give a broad overview of the key topics covered in this corpus.',
  },
  {
    label: 'Connections',
    question: 'Which entities in this knowledge graph are most connected, and what ties them together?',
  },
  {
    label: 'Deep dive',
    question: 'Pick the most important topic in the corpus and explain it in depth, citing the relevant sources.',
  },
];

const ROUTING_MODES = [
  { label: 'Auto', value: 'auto', hint: 'complexity heuristic picks the model' },
  { label: 'Fast', value: 'fast', hint: 'lookups in seconds' },
  { label: 'Deep', value: 'deep', hint: 'slowest, strongest synthesis' },
];

function confidenceBadge(conf: number | string | undefined): { text: string; cls: string } {
  if (typeof conf === 'number') {
    if (conf >= 0.8) return { text: `High ${conf}`, cls: 'tag growth' };
    if (conf >= 0.5) return { text: `Medium ${conf}`, cls: 'tag' };
    return { text: `Low ${conf}`, cls: 'tag attention' };
  }
  const c = String(conf ?? 'Medium').toLowerCase();
  if (c.includes('high')) return { text: 'High', cls: 'tag growth' };
  if (c.includes('low')) return { text: 'Low', cls: 'tag attention' };
  return { text: 'Medium', cls: 'tag' };
}

/** Keep only instrument-style entity tags: uppercase + digits + separators. */
function cleanEntities(raw: string[] | undefined): string[] {
  if (!raw) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const e of raw) {
    const t = e.trim();
    if (!/^[A-Z][A-Z0-9-]{2,}$/.test(t)) continue;
    if (seen.has(t)) continue;
    seen.add(t);
    out.push(t);
    if (out.length >= 6) break;
  }
  return out;
}

const PIPELINE_STEPS: StageKey[] = ['query', 'cache', 'retrieve', 'rerank', 'graph', 'llm', 'answer'];
const STEP_MS = [0, 450, 1000, 1550, 2100, 2650];

/** Record real query activity per domain so the revision dashboard can show
 *  times queried and last reviewed per topic. Kept on this device only. */
function logActivity(domainId: string, entities: string[]) {
  if (entities.length === 0) return;
  try {
    const key = `synapse_activity_${domainId}`;
    const log = JSON.parse(localStorage.getItem(key) || '[]') as { t: number; entities: string[] }[];
    log.push({ t: Date.now(), entities });
    localStorage.setItem(key, JSON.stringify(log.slice(-300)));
  } catch {
    /* ignore */
  }
}

export default function QueryPage() {
  const params = useParams<{ domain: string }>();
  const segment = params.domain ?? '';
  const { resolve } = useDomain();
  const domain = resolve(segment);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [routing, setRouting] = useState('auto');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<StageKey | null>(null);
  const [doneThrough, setDoneThrough] = useState<StageKey | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  };

  const scrollToEnd = () => endRef.current?.scrollIntoView({ behavior: 'smooth' });

  // Animate the pipeline stages while waiting for the first token, so the
  // wait reads as processing, not a hang.
  const startPipelineAnimation = () => {
    clearTimers();
    setActiveStage('query');
    setDoneThrough(null);
    PIPELINE_STEPS.slice(1, 6).forEach((stage, i) => {
      timersRef.current.push(
        setTimeout(() => {
          setDoneThrough(PIPELINE_STEPS[i]);
          setActiveStage(stage);
        }, STEP_MS[i + 1]),
      );
    });
  };

  useEffect(() => () => clearTimers(), []);

  // Deep link from the revision dashboard: prefill a topic-focused question.
  useEffect(() => {
    const t = setTimeout(() => {
      const topic = new URLSearchParams(window.location.search).get('topic');
      if (topic) setInput(`Explain ${topic} in depth, citing the sources.`);
    }, 0);
    return () => clearTimeout(t);
  }, []);

  async function ask(question: string) {
    if (!question.trim() || streaming || !domain) return;
    setError(null);
    setInput('');
    clearTimers();
    startPipelineAnimation();

    const userMsg: Message = { role: 'user', content: question };
    const assistantMsg: Message = { role: 'assistant', content: '', question };
    setMessages((m) => [...m, userMsg, assistantMsg]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const live = { content: '', gotTokens: false };
    let settled = false;

    const patch = (fn: (m: Message) => Message) =>
      setMessages((ms) => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)));

    try {
      await streamQuery(question, 5, routing, controller.signal, (ev) => {
        if (ev.type === 'token') {
          if (!live.gotTokens) {
            live.gotTokens = true;
            clearTimers();
            setActiveStage('llm');
            setDoneThrough('graph');
          }
          live.content += String(ev.content ?? '');
          patch((m) => ({ ...m, content: live.content }));
        } else if (ev.type === 'metadata') {
          const meta = (ev.content ?? {}) as Partial<QueryResponse>;
          settled = true;
          clearTimers();
          setActiveStage(null);
          setDoneThrough('answer');
          const entities = cleanEntities(meta.entities_used);
          patch((m) => ({
            ...m,
            content: String(meta.answer ?? live.content),
            confidence: meta.confidence,
            modelUsed: meta.model_used,
            latencyMs: meta.latency_ms,
            entities,
            keyPoints: meta.key_points ?? [],
            sources: meta.sources ?? [],
            trace: meta.trace,
          }));
          logActivity(domain.domain_id, entities);
        } else if (ev.type === 'error') {
          settled = true;
          clearTimers();
          setActiveStage(null);
          setDoneThrough(null);
          patch((m) => ({ ...m, content: String(ev.content) }));
        }
      }, domain.domain_id);
    } catch (e) {
      clearTimers();
      setActiveStage(null);
      setDoneThrough(null);
      if (e instanceof ApiError) {
        setError(e.message);
      } else if ((e as Error).name !== 'AbortError') {
        setError((e as Error).message);
      }
    } finally {
      if (!settled && live.content) {
        patch((m) => (m.content ? m : { ...m, content: live.content }));
      }
      setStreaming(false);
      abortRef.current = null;
      scrollToEnd();
    }
  }

  const lastTrace = messages[messages.length - 1]?.trace;

  if (!domain) {
    return (
      <div style={{ padding: '2rem' }}>
        <div className="skeleton" style={{ height: 32, marginBottom: '0.8rem' }} />
        <div className="skeleton" style={{ height: 200 }} />
      </div>
    );
  }

  return (
    <>
      <div className="page-head">
        <h1 className="page-title">Query console</h1>
        <p className="page-sub">
          Ask anything across {domain.display_name}. Answers trace back to the
          graph so you can see exactly where they came from.
        </p>
      </div>

      <div className="card" style={{ padding: '1.2rem 1.4rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', flexWrap: 'wrap', marginBottom: '0.9rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Routing</span>
          <div className="segmented">
            {ROUTING_MODES.map((r) => (
              <button
                key={r.value}
                className={routing === r.value ? 'active' : ''}
                onClick={() => setRouting(r.value)}
                title={r.hint}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
        >
          <textarea
            className="textarea"
            placeholder="Ask your corpus a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                ask(input);
              }
            }}
            disabled={streaming}
          />
          <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.6rem' }}>
            <button className="btn" type="submit" disabled={streaming || !input.trim()}>
              {streaming ? (
                <>
                  <CircleNotch size={14} style={{ marginRight: '0.4rem', verticalAlign: '-2px', animation: 'spin 1s linear infinite' }} />
                  Answering
                </>
              ) : (
                'Ask'
              )}
            </button>
            <button
              className="btn ghost"
              type="button"
              onClick={() => abortRef.current?.abort()}
              disabled={!streaming}
            >
              <X size={13} style={{ marginRight: '0.3rem', verticalAlign: '-2px' }} />
              Stop
            </button>
            {messages.length > 0 && (
              <button className="btn ghost" type="button" style={{ marginLeft: 'auto' }} onClick={() => setMessages([])}>
                Clear chat
              </button>
            )}
          </div>
        </form>

        <div className="chip-row" style={{ marginTop: '1rem', marginBottom: 0 }}>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              className="chip"
              onClick={() => ask(ex.question)}
              disabled={streaming}
              title={ex.question}
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="info-box error">
          <Prohibit size={14} style={{ marginRight: '0.4rem', verticalAlign: '-2px' }} />
          {error}
        </div>
      )}

      {streaming && activeStage && (
        <div className="pipeline">
          <PipelineRow active={activeStage} doneThrough={doneThrough ?? undefined} />
          <div className="stat-chips">
            <span className="stat-chip">routing: {routing}</span>
            <span className="stat-chip" style={{ color: 'var(--signal)' }}>
              {activeStage === 'llm' ? 'generating' : 'retrieving'}
            </span>
          </div>
        </div>
      )}

      {messages.map((m, i) => (
        <div key={i}>
          {m.role === 'user' ? (
            <div className="chat-user">{m.content}</div>
          ) : (
            <div className={`chat-assistant ${m.sources?.length ? 'has-pulse' : ''}`}>
              {m.sources && m.sources.length > 0 && <SignalPulse />}
              <div className="chat-meta">
                {(() => {
                  const b = confidenceBadge(m.confidence);
                  return (
                    <>
                      <span className={b.cls}>Confidence: {b.text}</span>
                      {m.modelUsed && <span className="tag signal">{m.modelUsed}</span>}
                      {typeof m.latencyMs === 'number' && (
                        <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                          {m.latencyMs} ms
                        </span>
                      )}
                    </>
                  );
                })()}
              </div>
              <div className={`chat-text ${m.content === '' && streaming && i === messages.length - 1 ? 'chat-cursor' : ''}`}>
                {m.content || (streaming ? '…' : '')}
              </div>
              {m.keyPoints && m.keyPoints.length > 0 && (
                <ul style={{ color: 'var(--text)', fontSize: '0.9rem', margin: '0.8rem 0 0', paddingLeft: '1.2rem' }}>
                  {m.keyPoints.map((kp, j) => (
                    <li key={j}>{kp}</li>
                  ))}
                </ul>
              )}
              {m.entities && m.entities.length > 0 && (
                <div style={{ marginTop: '0.6rem', display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center' }}>
                  {m.entities.map((e) => (
                    <Tag key={e} tone="default">{e}</Tag>
                  ))}
                </div>
              )}
              {m.sources && m.sources.length > 0 && (
                <div className="source-chips">
                  {m.sources.map((s, j) => {
                    const id = s.citation || s.doc_id || `source-${j + 1}`;
                    return (
                      <a
                        key={`${id}-${j}`}
                        className="source-chip"
                        href={`/${segment}/graph?node=${encodeURIComponent(id)}`}
                        title="Open in the graph"
                      >
                        {id}
                      </a>
                    );
                  })}
                </div>
              )}
              {m.trace || m.sources?.length ? (
                <div style={{ marginTop: '0.8rem' }}>
                  <EvidenceTrace trace={m.trace} sources={m.sources} />
                </div>
              ) : null}
            </div>
          )}
        </div>
      ))}
      <div ref={endRef} />

      {lastTrace && (
        <div className="info-box info" style={{ fontSize: '0.78rem' }}>
          <StatChips trace={lastTrace} />
        </div>
      )}
    </>
  );
}