'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import type { LlmStatus } from '@/lib/types';

const NAV = [
  { href: '/', label: '⚡ Query Console' },
  { href: '/documents', label: '📄 Documents' },
  { href: '/graph', label: '🕸️ Knowledge Network' },
  { href: '/entities', label: '🔍 Entity Explorer' },
  { href: '/evaluation', label: '📊 Evaluation' },
  { href: '/settings', label: '⚙️ Settings' },
];

type BackendState = 'checking' | 'online' | 'offline' | 'timeout';

const STATUS_TEXT: Record<BackendState, string> = {
  checking: 'connecting…',
  online: 'system online',
  offline: 'backend offline',
  timeout: 'reconnecting…',
};

export default function Sidebar() {
  const pathname = usePathname();
  const [state, setState] = useState<BackendState>('checking');
  const [llm, setLlm] = useState<LlmStatus | null>(null);
  const [retryTick, setRetryTick] = useState(0);
  const checkId = useRef(0);

  const check = useCallback(async () => {
    const id = ++checkId.current;
    setState('checking');

    // 8s cap — never hang on a cold/sleeping backend
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);

    try {
      const h = await api.health(controller.signal);
      clearTimeout(timer);
      if (id === checkId.current) setState(h.status === 'ok' ? 'online' : 'offline');
    } catch (e) {
      clearTimeout(timer);
      if (id !== checkId.current) return;
      setState((e as Error).name === 'AbortError' ? 'timeout' : 'offline');
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    const checkLlm = async () => {
      try {
        const l = await api.llmStatus();
        if (mounted) setLlm(l);
      } catch {
        /* keep null */
      }
    };
    check();
    checkLlm();
    const t = setInterval(check, 25000);
    return () => {
      mounted = false;
      clearInterval(t);
    };
  }, [check, retryTick]);

  const llmLabel = llm
    ? llm.nvidia_available
      ? 'LLM: NVIDIA'
      : llm.ollama_available
        ? 'LLM: Ollama'
        : 'LLM: fallback'
    : 'LLM: …';

  const dotColor =
    state === 'online' ? 'var(--phosphor-cyan)' : state === 'offline' ? 'var(--alert-red)' : 'var(--signal-amber)';
  const pulsing = state === 'checking' || state === 'timeout';

  return (
    <aside className="sidebar">
      <div className="brand">
        Synapse<span className="dot">.</span>
      </div>
      <div className="brand-sub">Knowledge Intelligence</div>

      {NAV.map((n) => (
        <Link
          key={n.href}
          href={n.href}
          className={`nav-link ${pathname === n.href ? 'active' : ''}`}
        >
          {n.label}
        </Link>
      ))}

      <div className="sidebar-status">
        <div className="row">
          <span
            className="status-badge unknown"
            style={{ padding: '0.3rem 0.6rem', fontSize: '0.68rem', borderColor: 'transparent', background: 'transparent' }}
          >
            <span
              className="led"
              style={{
                background: dotColor,
                boxShadow: pulsing ? `0 0 6px ${dotColor}` : 'none',
                animation: pulsing ? 'ledPulse 1.2s ease-in-out infinite' : 'none',
              }}
            />
            {STATUS_TEXT[state]}
          </span>
        </div>
        {(state === 'offline' || state === 'timeout') && (
          <button
            className="btn ghost"
            style={{ marginTop: '0.4rem', fontSize: '0.68rem', padding: '0.3rem 0.7rem' }}
            onClick={() => {
              setRetryTick((t) => t + 1);
              check();
            }}
          >
            ⟳ Retry
          </button>
        )}
        <div className="row" style={{ color: 'var(--text-dim)' }}>{llmLabel}</div>
        {state === 'checking' && (
          <div className="row" style={{ color: 'var(--text-dim)', fontStyle: 'normal' }}>
            waking up the model — first query takes a few seconds
          </div>
        )}
      </div>
    </aside>
  );
}
