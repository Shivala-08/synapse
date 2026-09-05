'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from './api';
import type { DomainInfo } from './types';

interface DomainCtx {
  domains: DomainInfo[];
  loading: boolean;
  /** Map a URL segment (e.g. "second-brain") to its domain profile. */
  resolve: (segment: string) => DomainInfo | undefined;
  /** Map a domain_id (e.g. "second_brain") to its URL segment. */
  segment: (domainId: string) => string;
}

export const toSegment = (domainId: string) => domainId.replace(/_/g, '-');
export const fromSegment = (segment: string) => segment.replace(/-/g, '_');

const DomainContext = createContext<DomainCtx>({
  domains: [],
  loading: true,
  resolve: () => undefined,
  segment: toSegment,
});

export function useDomain() {
  return useContext(DomainContext);
}

export function DomainProvider({ children }: { children: ReactNode }) {
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await api.domains();
        if (mounted) setDomains(res.domains ?? []);
      } catch {
        // backend unreachable - keep empty, pages show their own error state
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  const resolve = (segment: string) => {
    const id = fromSegment(segment);
    return domains.find((d) => d.domain_id === id);
  };

  return (
    <DomainContext.Provider value={{ domains, loading, resolve, segment: toSegment }}>
      {children}
    </DomainContext.Provider>
  );
}