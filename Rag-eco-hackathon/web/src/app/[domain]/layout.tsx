'use client';

import { useEffect } from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import { useDomain } from '@/lib/DomainContext';
import Rail from '@/components/Rail';

export default function DomainLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ domain: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const { domains, resolve } = useDomain();

  const domain = resolve(params.domain ?? '');

  // Unknown segment: bounce to the default domain once the list is loaded.
  useEffect(() => {
    if (domains.length === 0) return;
    if (!domain) router.replace('/second-brain/query');
  }, [domain, domains.length, router]);

  if (!domain) return null;

  const collapsed = pathname?.endsWith('/graph') ?? false;

  return (
    <div className="app-shell">
      <Rail domain={domain} collapsed={collapsed} />
      <main className={`main ${collapsed ? 'fullbleed' : ''}`}>{children}</main>
    </div>
  );
}