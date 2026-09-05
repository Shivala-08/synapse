'use client';

/**
 * Metric - a display number with a caption label. Every data number in the
 * app (mastery, latency, counts) renders through this so it reads as an
 * instrument readout, never prose.
 */
export function Metric({
  value,
  label,
  color,
}: {
  value: string | number;
  label: string;
  color?: 'attention' | 'growth' | 'signal' | 'danger' | 'default';
}) {
  const cls =
    color === 'attention' ? 'var(--attention)'
    : color === 'growth' ? 'var(--growth)'
    : color === 'signal' ? 'var(--signal)'
    : color === 'danger' ? 'var(--danger)'
    : 'var(--text)';
  return (
    <div className="stat-card">
      <div className="value" style={{ color: cls }}>{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}

/**
 * Tag - chip for entity identifiers (EQ-1002, OISD-116, WO-2026-1001) and
 * other tag-like data. Growth (teal) by default; pass a tone for variants.
 */
export function Tag({
  children,
  tone = 'cyan',
  title,
}: {
  children: React.ReactNode;
  tone?: 'cyan' | 'amber' | 'red' | 'green' | 'signal' | 'default';
  title?: string;
}) {
  const cls =
    tone === 'cyan' || tone === 'green' ? 'tag growth'
    : tone === 'amber' ? 'tag attention'
    : tone === 'red' ? 'tag attention'
    : tone === 'signal' ? 'tag signal'
    : 'tag';
  return (
    <span className={cls} title={title}>
      {children}
    </span>
  );
}