'use client';

import { useRef, useState } from 'react';
import Hero from '@/components/Hero';
import { api } from '@/lib/api';
import { Tag } from '@/components/primitives';
import type { IngestInitializeResponse, DebugHit, IngestUploadResult } from '@/lib/types';

export default function SettingsPage() {
  const [initializing, setInitializing] = useState(false);
  const [initResult, setInitResult] = useState<IngestInitializeResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<IngestUploadResult[] | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dq, setDq] = useState('quarterly inspection');
  const [dn, setDn] = useState(5);
  const [hits, setHits] = useState<DebugHit[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function initialize() {
    setInitializing(true);
    setError(null);
    try {
      setInitResult(await api.ingestInitialize());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setInitializing(false);
    }
  }

  async function upload() {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      setUploadResults((await api.ingestUpload(files)).results);
      if (fileRef.current) fileRef.current.value = '';
      setFiles([]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  async function debugSearch() {
    setError(null);
    try {
      setHits((await api.debugSearch(dq, dn)).hits);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <Hero title="Settings & Control" subtitle="Manage the vector database, ingest documents, and debug retrieval" />

      {error && <div className="info-box error">⚠️ {error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>Core corpus initialization</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
            Index all pre-bundled files: OISD / DGMS / Factory Act regulatory docs plus synthetic work
            orders, permits, and incident reports.
          </p>
          <button className="btn" onClick={initialize} disabled={initializing}>
            {initializing ? '⏳ Parsing, embedding, building graph…' : 'Scan & Index Default Corpus'}
          </button>
          {initResult && (
            <div className="info-box success" style={{ marginTop: '0.8rem' }}>
              ✅ Indexed {initResult.stats.files_ingested} documents · {initResult.stats.total_chunks} chunks
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>Upload new documents</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
            Upload PDF, DOCX, CSV, or TXT files to add to the live search index.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.pdf,.docx,.csv"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            style={{ marginBottom: '0.8rem' }}
          />
          <button className="btn" onClick={upload} disabled={uploading || files.length === 0}>
            {uploading ? '⏳ Ingesting…' : `Ingest ${files.length} file(s)`}
          </button>
          {uploadResults && (
            <div style={{ marginTop: '0.8rem' }}>
              {uploadResults.map((r, i) => (
                <div
                  key={i}
                  className={r.status === 'success' ? 'info-box success' : 'info-box error'}
                  style={{ marginBottom: '0.5rem', padding: '0.5rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  {r.status === 'success' ? '✅' : '❌'}{' '}
                  <Tag tone={r.status === 'success' ? 'green' : 'red'}>{r.doc_id ?? r.filename ?? 'unknown'}</Tag>
                  <span>{r.status === 'success' ? `· ${r.chunk_count} chunks indexed` : `· ${r.error}`}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <div className="section-title" style={{ marginTop: 0 }}>Debug: raw vector search</div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
          Test retrieval quality without the LLM — great for tuning chunk size / top-k.
        </p>
        <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap', marginBottom: '0.8rem' }}>
          <input className="input" style={{ flex: 1, minWidth: 220 }} value={dq} onChange={(e) => setDq(e.target.value)} />
          <input
            className="input"
            style={{ width: 90 }}
            type="number"
            min={1}
            max={10}
            value={dn}
            onChange={(e) => setDn(Number(e.target.value))}
          />
          <button className="btn" onClick={debugSearch}>Run debug search</button>
        </div>
        {hits && (
          <>
            <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              {hits.length} hits
            </div>
            {hits.map((h) => (
              <div className="citation" key={h.rank}>
                <div className="cite-header">[{h.rank}] {h.doc_id} — score: {h.score.toFixed(4)}</div>
                <div className="cite-text">{h.excerpt}</div>
              </div>
            ))}
          </>
        )}
      </div>
    </>
  );
}
