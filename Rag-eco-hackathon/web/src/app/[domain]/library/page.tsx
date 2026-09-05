'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { UploadSimple, ArrowsClockwise, FileText } from '@phosphor-icons/react';
import { api } from '@/lib/api';
import { useDomain } from '@/lib/DomainContext';
import type { DocumentMeta } from '@/lib/types';

function fmtDate(iso: string | undefined): string {
  if (!iso) return 'unknown date';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'unknown date';
  return d.toLocaleDateString();
}

export default function LibraryPage() {
  const params = useParams<{ domain: string }>();
  const { resolve } = useDomain();
  const domain = resolve(params.domain ?? '');
  const domainId = domain?.domain_id;

  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState<{ kind: 'ok' | 'warn'; text: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    if (!domainId) return;
    setLoading(true);
    setError(null);
    try {
      setDocs(await api.documents(domainId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [domainId]);

  // Deferred so the initial fetch's state updates never run synchronously
  // inside the effect body (react-hooks/set-state-in-effect).
  useEffect(() => {
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, [load]);

  const uploadFiles = async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length || !domainId || uploading) return;
    setUploading(true);
    setNotice(null);
    setError(null);
    try {
      const res = await api.ingestUpload(list, domainId);
      const queued = res.results.filter((r) => r.status === 'queued').length;
      const failed = res.results.filter((r) => r.status === 'error');
      const parts: string[] = [];
      if (queued > 0) parts.push(`${queued} file${queued === 1 ? '' : 's'} queued for ingestion.`);
      if (failed.length) parts.push(failed.map((f) => f.error).join(' '));
      if (parts.length) setNotice({ kind: failed.length ? 'warn' : 'ok', text: parts.join(' ') });
      // Background ingest: refresh once after a beat, then again to catch stragglers.
      setTimeout(load, 4000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const reSync = async () => {
    if (!domainId || syncing) return;
    setSyncing(true);
    setNotice(null);
    setError(null);
    try {
      const r = await api.reSync(domainId);
      const text = r.added.length
        ? `Added ${r.added.length} new file${r.added.length === 1 ? '' : 's'} from the source folder.`
        : `Source folder up to date, ${r.skipped_count} file${r.skipped_count === 1 ? '' : 's'} already indexed.`;
      setNotice({ kind: 'ok', text });
      if (r.errors.length) {
        setNotice((n) => ({ kind: 'warn', text: `${n?.text ?? ''} ${r.errors.map((e) => e.error).join(' ')}` }));
      }
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSyncing(false);
    }
  };

  if (!domain) return <div className="skeleton" style={{ height: 240 }} />;

  const mostRecent = docs.length
    ? docs.reduce((a, b) => (a.upload_date > b.upload_date ? a : b))
    : null;
  const totalChunks = docs.reduce((n, d) => n + (d.chunk_count || 0), 0);

  return (
    <>
      <div className="page-head">
        <h1 className="page-title">Document library</h1>
        <p className="page-sub">
          Every source in {domain.display_name}, what it contains, and when it
          was added.
        </p>
      </div>

      {error && <div className="info-box error">{error}</div>}
      {notice && (
        <div className={`info-box ${notice.kind === 'ok' ? 'success' : 'warning'}`}>{notice.text}</div>
      )}

      <div
        className={`dropzone ${dragOver ? 'over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); uploadFiles(e.dataTransfer.files); }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".txt,.csv,.pdf,.docx,.md,.pptx"
          onChange={(e) => { if (e.target.files) uploadFiles(e.target.files); e.target.value = ''; }}
        />
        <UploadSimple size={22} color="var(--signal)" />
        <div style={{ fontWeight: 600, marginTop: '0.3rem' }}>
          {uploading ? 'Uploading and queuing...' : `Drop files here or click to upload to ${domain.display_name}`}
        </div>
        <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>
          txt, csv, pdf, docx, md, pptx
        </div>
      </div>

      <div className="section-title">Sources</div>
      {loading ? (
        <div className="skeleton" style={{ height: 44, marginBottom: '0.5rem' }} />
      ) : docs.length === 0 ? (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>No sources yet</div>
          <p style={{ color: 'var(--text-muted)', maxWidth: '60ch' }}>
            Upload files above, or re-sync from the source folder to pull in
            everything already there.
          </p>
        </div>
      ) : (
        <>
          <div className="stat-grid" style={{ marginBottom: '0.9rem' }}>
            <div className="stat-card"><div className="value signal">{docs.length}</div><div className="label">sources</div></div>
            <div className="stat-card"><div className="value">{totalChunks}</div><div className="label">chunks</div></div>
            <div className="stat-card"><div className="value growth">{mostRecent ? fmtDate(mostRecent.upload_date) : '—'}</div><div className="label">most recent source</div></div>
          </div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {docs.map((d) => (
              <div className="doc-row" key={d.doc_id}>
                <FileText size={16} color="var(--text-dim)" style={{ flexShrink: 0 }} />
                <div className="doc-info">
                  <div className="doc-name">{d.filename}</div>
                  <div className="doc-meta">
                    <span>{d.type}</span>
                    <span>{d.chunk_count} chunks</span>
                    {typeof d.entities_found === 'number' && <span>{d.entities_found} entities</span>}
                    <span>{fmtDate(d.upload_date)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="divider" />

      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>Source folder sync</div>
        <p style={{ color: 'var(--text-muted)', maxWidth: '62ch', fontSize: '0.86rem' }}>
          {domain.domain_id === 'second_brain'
            ? 'This domain mirrors an external vault. Re-sync scans the source folder and ingests anything not yet indexed.'
            : 'Re-sync scans the domain source folder and ingests files that are not yet indexed.'}
        </p>
        <button className="btn ghost" onClick={reSync} disabled={syncing || loading}>
          <ArrowsClockwise size={14} style={{ marginRight: '0.35rem', verticalAlign: '-2px' }} />
          {syncing ? 'Syncing...' : 'Re-sync from source'}
        </button>
      </div>
    </>
  );
}