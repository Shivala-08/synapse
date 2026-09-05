'use client';

export function SectionPlaceholder({
  title,
  description,
  planned,
}: {
  title: string;
  description: string;
  planned: string[];
}) {
  return (
    <>
      <div className="page-head">
        <h1 className="page-title">{title}</h1>
        <p className="page-sub">{description}</p>
      </div>
      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>Next in the build order</div>
        <p style={{ color: 'var(--text-muted)', maxWidth: '60ch', marginBottom: '0.6rem' }}>
          This view is scoped as a follow-up pass. It will render from real
          backend data once the core console and graph are locked.
        </p>
        <ul style={{ color: 'var(--text-muted)', paddingLeft: '1.2rem', margin: 0 }}>
          {planned.map((p) => (
            <li key={p} style={{ marginBottom: '0.3rem' }}>{p}</li>
          ))}
        </ul>
      </div>
    </>
  );
}