'use client';

import { useEffect, useState } from 'react';
import Hero from '@/components/Hero';
import { api } from '@/lib/api';
import { Tag } from '@/components/primitives';
import type { DocumentDetail, DocumentMeta } from '@/lib/types';

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentMeta[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [openDoc, setOpenDoc] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    api
      .documents()
      .then(setDocs)
      .catch((e) => setError((e as Error).message));
  }, []);

  async function toggleDoc(docId: string) {
    if (openDoc === docId) {
      setOpenDoc(null);
      setDetail(null);
      return;
    }
    setOpenDoc(docId);
    setLoadingDetail(true);
    setDetail(null);
    try {
      setDetail(await api.document(docId));
    } catch (e) {
      setDetail(null);
      setError((e as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  }

  const types = docs ? Array.from(new Set(docs.map((d) => d.type))).sort() : [];
  const filtered = (docs ?? []).filter(
    (d) =>
      (filterType === 'all' || d.type === filterType) &&
      (!search || d.filename.toLowerCase().includes(search.toLowerCase())),
  );

  return (
    <>
      <Hero title="Document Library" subtitle="Browse indexed regulatory documents and structured plant logs" />

      {error && <div className="info-box error">⚠️ {error}</div>}
      {!docs && !error && <div className="skeleton" style={{ height: 120 }} />}

      {docs && (
        <>
          <div className="stat-grid">
            <div className="stat-card"><div className="value">{docs.length}</div><div className="label">Total docs</div></div>
            <div className="stat-card"><div className="value">{filtered.length}</div><div className="label">Showing</div></div>
            <div className="stat-card"><div className="value">{types.length}</div><div className="label">Types</div></div>
          </div>

          <div style={{ display: 'flex', gap: '0.8rem', marginBottom: '1.2rem' }}>
            <select className="select" style={{ width: '220px' }} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="all">All types</option>
              {types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input
              className="input"
              placeholder="Search document names…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {filtered.map((d) => (
            <div key={d.doc_id}>
              <div className="doc-card">
                <div>
                  <h3>{d.filename}</h3>
                  <div className="doc-meta" style={{ alignItems: 'center' }}>
                    <Tag>{d.type}</Tag>
                    <span>{d.chunk_count} chunks</span>
                    <span>{d.upload_date}</span>
                    {d.entities_found != null && <span>{d.entities_found} entities</span>}
                  </div>
                </div>
                <button className="btn ghost" onClick={() => toggleDoc(d.doc_id)}>
                  {openDoc === d.doc_id ? 'Close' : 'Inspect chunks'}
                </button>
              </div>

              {openDoc === d.doc_id && (
                <details className="expander" open>
                  <div className="expander-body">
                    {loadingDetail && <div className="skeleton" style={{ height: 60 }} />}
                    {detail && (
                      <>
                        <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.6rem' }}>
                          {detail.chunks.length} chunks
                        </div>
                        {detail.chunks.map((c, i) => (
                          <div key={c.chunk_id} className="citation">
                            <div className="cite-header">
                              Chunk {String(c.metadata?.chunk_index ?? i)} · {c.chunk_id}
                            </div>
                            <div className="cite-text">{c.text}</div>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </details>
              )}
            </div>
          ))}

          {filtered.length === 0 && <div className="info-box info">No documents match the current filters.</div>}
        </>
      )}
    </>
  );
}
