'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { toSegment } from '@/lib/DomainContext';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    let mounted = true;
    (async () => {
      let target = '/second-brain/query';
      try {
        const res = await api.domains();
        if (mounted) {
          const list = res.domains ?? [];
          const saved = typeof window !== 'undefined' ? localStorage.getItem('synapse_active_domain') : null;
          const pick = saved && list.some((d) => d.domain_id === saved)
            ? saved
            : (list[0]?.domain_id ?? 'second_brain');
          target = `/${toSegment(pick)}/query`;
        }
      } catch {
        // backend unreachable - default to second-brain
      }
      if (mounted) router.replace(target);
    })();
    return () => { mounted = false; };
  }, [router]);

  return (
    <div style={{ padding: '2rem', maxWidth: 640 }}>
      <div className="skeleton" style={{ height: 48, marginBottom: '0.8rem' }} />
      <div className="skeleton" style={{ height: 24, marginBottom: '0.8rem' }} />
      <div className="skeleton" style={{ height: 24 }} />
    </div>
  );
}