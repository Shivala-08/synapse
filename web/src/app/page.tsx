'use client';

import { useEffect, useRef, useState } from 'react';
import Hero from '@/components/Hero';
import EvidenceTrace, { PipelineRow, StatChips, type StageKey } from '@/components/EvidenceTrace';
import { Tag } from '@/components/primitives';
import { ApiError, streamQuery } from '@/lib/api';
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

const EXAMPLES: { label: string; category: string; question: string }[] = [
  { label: '⚡ Simple lookup', category: 'Simple lookup', question: 'What are the electrical safety requirements per OISD-130?' },
  { label: '🔗 Multi-hop', category: 'Multi-hop', question: 'Which regulation applies to work order WO-2026-1001?' },
  { label: '⚖️ Contradiction', category: 'Contradiction', question: 'Do the safety manual and OISD-117 disagree on the internal inspection frequency for tank TNK-T03?' },
  { label: '📋 Compliance gap', category: 'Compliance gap', question: 'Is there a documented requirement for lockout/tagout procedures?' },
  { label: '🗂️ Record lookup', category: 'Record lookup', question: 'What is the current status of permit PRM-2026-5000?' },
];

const CATEGORIES = ['Simple lookup', 'Multi-hop', 'Contradiction', 'Compliance gap', 'Record lookup'];

const ROUTING_MODES = [
  { label: 'Auto Classifier', value: 'auto', hint: 'complexity heuristic picks 8B or 550B' },
  { label: 'Fast Answer (8B)', value: 'fast', hint: 'lookups in seconds' },
  { label: 'Deep Reasoning (550B)', value: 'deep', hint: 'slowest, strongest synthesis' },
];

function confidenceBadge(conf: number | string | undefined): { text: string; cls: string } {
  if (typeof conf === 'number') {
    if (conf >= 0.8) return { text: `High · ${conf}`, cls: 'badge-green' };
    if (conf >= 0.5) return { text: `Medium · ${conf}`, cls: 'badge-yellow' };
    return { text: `Low · ${conf}`, cls: 'badge-red' };
  }
  const c = String(conf ?? 'Medium').toLowerCase();
  if (c.includes('high')) return { text: 'High', cls: 'badge-green' };
  if (c.includes('low')) return { text: 'Low', cls: 'badge-red' };
  return { text: 'Medium', cls: 'badge-yellow' };
}

/**
 * The backend's entity extractor returns junk spans ("section 48", "oisd - 117").
 * Keep only instrument-style tags: uppercase + digits + separators.
 */
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
const STEP_MS = [0, 450, 1000, 1550, 2100, 2650]; // query→cache→retrieve→rerank→graph→llm

export default function ChatPage() {
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
          setDoneThrough(PIPELINE_STEPS[i]); // previous stage done
          setActiveStage(stage);
        }, STEP_MS[i + 1]),
      );
    });
  };

  useEffect(() => () => clearTimers(), []);

  async function ask(question: string) {
    if (!question.trim() || streaming) return;
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
            setDoneThrough('graph'); // retrieval chain complete — generation underway
          }
          live.content += String(ev.content ?? '');
          patch((m) => ({ ...m, content: live.content }));
        } else if (ev.type === 'metadata') {
          const meta = (ev.content ?? {}) as Partial<QueryResponse>;
          settled = true;
          clearTimers();
          setActiveStage(null);
          setDoneThrough('answer');
          patch((m) => ({
            ...m,
            content: String(meta.answer ?? live.content),
            confidence: meta.confidence,
            modelUsed: meta.model_used,
            latencyMs: meta.latency_ms,
            entities: cleanEntities(meta.entities_used),
            keyPoints: meta.key_points ?? [],
            sources: meta.sources ?? [],
            trace: meta.trace,
          }));
        } else if (ev.type === 'error') {
          settled = true;
          clearTimers();
          setActiveStage(null);
          setDoneThrough(null);
          patch((m) => ({ ...m, content: `⚠️ ${String(ev.content)}` }));
        }
      });
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

  const consoleRef = useRef<HTMLDivElement | null>(null);
  const scrollToConsole = () =>
    consoleRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const lastTrace = messages[messages.length - 1]?.trace;
  const lastSources = messages[messages.length - 1]?.sources;

  return (
    <>
      <Hero
        title="Graph-Augmented Knowledge Intelligence"
        subtitle="Hybrid retrieval, knowledge-graph reasoning, and adaptive model routing — measured, not just claimed."
        ctas={[
          { label: 'Ask a question', onClick: scrollToConsole },
          { label: 'See the evaluation', href: '/evaluation', variant: 'ghost' },
        ]}
      />

      <div ref={consoleRef} className="card" style={{ padding: '1.2rem 1.4rem' }}>
        <div className="section-title" style={{ marginTop: 0 }}>Query console</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', flexWrap: 'wrap', marginBottom: '0.9rem' }}>
          <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Router
          </span>
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

        <div className="chip-row" style={{ marginBottom: '0.6rem' }}>
          {CATEGORIES.map((c) => (
            <button
              key={c}
              className="chip"
              onClick={() => {
                const ex = EXAMPLES.find((e) => e.category === c);
                if (ex) ask(ex.question);
              }}
              disabled={streaming}
            >
              {c}
            </button>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
        >
          <textarea
            className="textarea"
            placeholder="Ask a safety or regulatory question… e.g. “Which regulation applies to work order WO-2026-1001?”"
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
              {streaming ? '⏳ Answering…' : 'Ask Synapse'}
            </button>
            <button
              className="btn ghost"
              type="button"
              onClick={() => abortRef.current?.abort()}
              disabled={!streaming}
            >
              ✕ Stop
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
              className="chip amber"
              onClick={() => ask(ex.question)}
              disabled={streaming}
              title={ex.question}
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="info-box error">⚠️ {error}</div>}

      {/* Live pipeline visualizer while streaming */}
      {streaming && activeStage && (
        <div className="pipeline">
          <PipelineRow active={activeStage} doneThrough={doneThrough ?? undefined} />
          <div className="stat-chips">
            <span className="stat-chip">routing: {routing}</span>
            <span className="stat-chip" style={{ color: 'var(--signal-amber)' }}>
              {activeStage === 'llm' ? 'generating…' : 'retrieving…'}
            </span>
          </div>
        </div>
      )}

      {messages.map((m, i) => (
        <div key={i}>
          {m.role === 'user' ? (
            <div className="chat-user">{m.content}</div>
          ) : (
            <div className="chat-assistant">
              <div className="chat-meta">
                {(() => {
                  const b = confidenceBadge(m.confidence);
                  return (
                    <>
                      <span className={`badge ${b.cls}`}>Confidence: {b.text}</span>
                      {m.modelUsed && <span className="badge badge-cyan">{m.modelUsed}</span>}
                      {typeof m.latencyMs === 'number' && (
                        <span className="badge badge-gray">⏱ {m.latencyMs} ms</span>
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
                  <span className="mono" style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    Entities
                  </span>
                  {m.entities.map((e) => (
                    <Tag key={e}>{e}</Tag>
                  ))}
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
