'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import {
  ChatCircleDots,
  Graph,
  Gauge,
  MapTrifold,
  Archive,
  ArrowClockwise,
} from '@phosphor-icons/react';
import { API_URL } from '@/lib/api';
import { useDomain, toSegment } from '@/lib/DomainContext';
import type { DomainInfo } from '@/lib/types';

type DomainDot = Record<string, 'up' | 'off'>;

function useDomainStatus(domains: DomainInfo[]) {
  const [dots, setDots] = useState<DomainDot>({});

  const probe = useCallback(async () => {
    const next: DomainDot = {};
    await Promise.all(
      domains.map(async (d) => {
        try {
          const ctrl = new AbortController();
          const t = setTimeout(() => ctrl.abort(), 4000);
          const res = await fetch(
            `${API_URL}/documents?domain_id=${encodeURIComponent(d.domain_id)}`,
            { signal: ctrl.signal },
          );
          clearTimeout(t);
          next[d.domain_id] = res.ok ? 'up' : 'off';
        } catch {
          next[d.domain_id] = 'off';
        }
      }),
    );
    setDots(next);
  }, [domains]);

  useEffect(() => {
    if (domains.length === 0) return;
    // Defer the first probe so state updates never run synchronously inside
    // the effect body (react-hooks/set-state-in-effect).
    const first = setTimeout(probe, 0);
    const t = setInterval(probe, 30000);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [domains, probe]);

  return dots;
}

export default function Rail({ domain, collapsed }: { domain: DomainInfo; collapsed?: boolean }) {
  const pathname = usePathname();
  const { domains } = useDomain();
  const dots = useDomainStatus(domains);

  const navFor = (d: DomainInfo) => {
    const seg = toSegment(d.domain_id);
    const base = `/${seg}`;
    return [
      { href: `${base}/query`, label: 'Query', icon: <ChatCircleDots size={17} /> },
      { href: `${base}/graph`, label: 'Graph', icon: <Graph size={17} /> },
      ...(d.domain_id === 'exam_prep'
        ? [
            { href: `${base}/revision`, label: 'Revision', icon: <Gauge size={17} /> },
            { href: `${base}/roadmap`, label: 'Roadmap', icon: <MapTrifold size={17} /> },
          ]
        : []),
      { href: `${base}/library`, label: 'Library', icon: <Archive size={17} /> },
    ];
  };

  return (
    <aside className={`rail glass ${collapsed ? 'collapsed' : ''}`}>
      <div className="glass-body">
        <div className="brand">
          <span className="brand-word">Synapse</span>
          <span className="dot">.</span>
        </div>
        <div className="brand-sub">Knowledge intelligence</div>

        <div className="domain-switch">
          {domains.map((d) => {
            const active = d.domain_id === domain.domain_id;
            const seg = toSegment(d.domain_id);
            return (
              <Link
                key={d.domain_id}
                href={`/${seg}/query`}
                className={`domain-opt ${active ? 'active' : ''}`}
                title={d.display_name}
              >
                <span className={`led ${dots[d.domain_id] === 'up' ? 'up' : ''}`} />
                <span className="dname">{d.display_name}</span>
              </Link>
            );
          })}
        </div>

        <hr className="rail-divider" />

        {navFor(domain).map((n) => {
          const active = pathname === n.href;
          return (
            <Link key={n.href} href={n.href} className={`nav-link ${active ? 'active' : ''}`}>
              <span className="nav-ico">{n.icon}</span>
              <span className="nav-label">{n.label}</span>
            </Link>
          );
        })}

        <div className="rail-status">
          <div className="row">
            <span className={`led ${dots[domain.domain_id] === 'up' ? 'on' : 'off'}`} />
            <span className="rail-status-text">
              {dots[domain.domain_id] === 'up' ? `${domain.display_name} collection up` : 'collection unreachable'}
            </span>
          </div>
          <div className="row">
            <ArrowClockwise size={12} />
            <span className="rail-status-text">{domain.display_name}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}