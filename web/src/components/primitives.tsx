'use client';

/**
 * Metric — a mono value with a caption label. Every number in the app
 * (latency, similarity, accuracy, MRR…) renders through this so data always
 * reads as an instrument readout, never prose.
 */
export function Metric({
  value,
  label,
  color,
}: {
  value: string | number;
  label: string;
  color?: 'amber' | 'cyan' | 'red' | 'default';
}) {
  const cls =
    color === 'amber' ? 'var(--signal-amber)' : color === 'cyan' ? 'var(--phosphor-cyan)' : color === 'red' ? 'var(--alert-red)' : 'var(--text)';
  return (
    <div className="stat-card">
      <div className="value" style={{ color: cls }}>{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}

/**
 * Tag — mono chip for entity identifiers (EQ-1002, OISD-116, WO-2026-1001)
 * and other tag-like data. Cyan by default; pass tone for variants.
 */
export function Tag({
  children,
  tone = 'cyan',
  title,
}: {
  children: React.ReactNode;
  tone?: 'cyan' | 'amber' | 'red' | 'green' | 'default';
  title?: string;
}) {
  const cls =
    tone === 'cyan' ? 'tag' : tone === 'amber' ? 'badge badge-yellow' : tone === 'red' ? 'badge badge-red' : tone === 'green' ? 'badge badge-green' : 'badge badge-gray';
  return (
    <span className={cls} title={title}>
      {children}
    </span>
  );
}
