'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';

type Status = 'checking' | 'online' | 'offline' | 'timeout';

const STATUS_TEXT: Record<Status, string> = {
  checking: 'waking up the model…',
  online: '● System Online',
  offline: '○ Backend Offline',
  timeout: 'reconnecting…',
};

export interface HeroCta {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: 'primary' | 'ghost';
}

export default function Hero({
  title,
  subtitle,
  ctas,
}: {
  title: string;
  subtitle: string;
  ctas?: HeroCta[];
}) {
  const [status, setStatus] = useState<Status>('checking');
  const [retryTick, setRetryTick] = useState(0);
  const checkId = useRef(0);

  const check = useCallback(async () => {
    const id = ++checkId.current;
    setStatus('checking');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000); // never hang silently
    try {
      const h = await api.health(controller.signal);
      clearTimeout(timer);
      if (id === checkId.current) setStatus(h.status === 'ok' ? 'online' : 'offline');
    } catch (e) {
      clearTimeout(timer);
      if (id !== checkId.current) return;
      setStatus((e as Error).name === 'AbortError' ? 'timeout' : 'offline');
    }
  }, []);

  useEffect(() => {
    check();
    const t = setInterval(check, 25000);
    return () => clearInterval(t);
  }, [check, retryTick]);

  const badgeCls =
    status === 'online' ? 'on' : status === 'offline' ? 'off' : 'unknown';

  return (
    <div className="hero">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
        {ctas && ctas.length > 0 && (
          <div className="hero-ctas">
            {ctas.map((c) =>
              c.href ? (
                <Link key={c.label} href={c.href} className={c.variant === 'ghost' ? 'btn ghost' : 'btn'}>
                  {c.label}
                </Link>
              ) : (
                <button key={c.label} className={c.variant === 'ghost' ? 'btn ghost' : 'btn'} onClick={c.onClick}>
                  {c.label}
                </button>
              ),
            )}
          </div>
        )}
      </div>
      <div className="hero-meta">
        <span className={`status-badge ${badgeCls}`}>
          <span className="led" />
          {STATUS_TEXT[status]}
        </span>
        {status === 'offline' || status === 'timeout' ? (
          <div style={{ marginTop: '0.4rem' }}>
            <button
              className="btn ghost"
              style={{ fontSize: '0.68rem', padding: '0.28rem 0.7rem' }}
              onClick={() => {
                setRetryTick((t) => t + 1);
                check();
              }}
            >
              ⟳ Retry
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
