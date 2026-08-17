'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Hero from '@/components/Hero';
import { api, API_URL } from '@/lib/api';
import { Tag } from '@/components/primitives';
import type { GraphEdge, GraphNodeDetail } from '@/lib/types';

// react-force-graph-2d uses canvas and needs to run client-side only
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface FGNode {
  id: string;
  type?: string;
  color?: string;
  val?: number;
  x?: number;
  y?: number;
}

interface FGLink {
  source: string;
  target: string;
  relation?: string;
}

const TYPE_COLORS: Record<string, string> = {
  equipment: '#4DD8C0', regulation: '#FFA630', plant: '#34C77B',
  permit: '#f59e0b', work_order: '#8b5cf6', incident: '#ec4899',
  inspection: '#06b6d4', person: '#f97316', hazard: '#E5484D',
  permit_type: '#d97706', incident_type: '#db2777',
};

const TYPE_LABELS: Record<string, string> = {
  equipment: 'EQUIPMENT', regulation: 'REGULATION', plant: 'PLANT',
  permit: 'PERMIT', work_order: 'WORK ORDER', incident: 'INCIDENT',
  inspection: 'INSPECTION', person: 'PERSON', hazard: 'HAZARD',
};

// A representative equipment→regulation traversal shown on first load, so the
// canvas is never empty: the graph is doing something within one second.
const AUTO_PATH: [string, string] = ['EQ-1002', 'OISD-116'];

export default function GraphPage() {
  const [nodes, setNodes] = useState<FGNode[]>([]);
  const [links, setLinks] = useState<FGLink[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<GraphNodeDetail | null>(null);
  const [search, setSearch] = useState('');
  const [pathSrc, setPathSrc] = useState('');
  const [pathTgt, setPathTgt] = useState('');
  const [pathResult, setPathResult] = useState<{ path: string[]; edges: GraphEdge[]; length: number } | null>(null);
  const [width, setWidth] = useState(0);
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const measure = () => setWidth(containerRef.current?.clientWidth ?? 0);
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  async function loadGraph(maxNodes: number) {
    setLoading(true);
    try {
      const g = await api.graph(maxNodes);
      setNodes(g.nodes.map((n) => ({
        id: n.id,
        type: n.type,
        color: n.color || TYPE_COLORS[n.type ?? ''] || '#8394A6',
        val: 1,
      })));
      setLinks(g.edges.map((e) => ({ source: e.from, target: e.to, relation: e.relation })));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function applyPath(r: { path: string[]; edges: GraphEdge[]; length: number }, visible: FGNode[]) {
    const pathSet = new Set(r.path);
    setNodes(visible.filter((n) => pathSet.has(n.id)));
    setLinks((r.edges ?? []).map((e) => ({ source: e.from, target: e.to, relation: e.relation })));
    setPathResult(r);
  }

  // Load the full graph, then auto-highlight a representative traversal.
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const g = await api.graph(200);
        const mappedNodes = g.nodes.map((n) => ({
          id: n.id,
          type: n.type,
          color: n.color || TYPE_COLORS[n.type ?? ''] || '#8394A6',
          val: 1,
        }));
        const mappedLinks = g.edges.map((e) => ({ source: e.from, target: e.to, relation: e.relation }));
        setNodes(mappedNodes);
        setLinks(mappedLinks);
        // best-effort auto path — never fails the page if entities are absent
        try {
          const r = await api.graphPath(AUTO_PATH[0], AUTO_PATH[1]);
          if (r && !r.error && r.path && r.path.length > 1) {
            applyPath({ path: r.path, edges: r.path_edges ?? [], length: r.length ?? r.path.length - 1 }, mappedNodes);
          }
        } catch { /* fall back to full graph */ }
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const graphData = useMemo(() => ({ nodes, links }), [nodes, links]);

  async function onNodeClick(node: any) {
    try {
      const d = await api.graphNode(String(node.id));
      if (!d || 'error' in d) {
        setSelected(null);
        return;
      }
      setSelected(d);
      graphRef.current?.centerAt(node.x, node.y, 600);
      graphRef.current?.zoom(2.5, 600);
    } catch {
      setSelected(null);
    }
  }

  async function doSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!search.trim()) return;
    try {
      const res = await fetch(`${API_URL}/graph/search?q=${encodeURIComponent(search)}&limit=5`);
      if (!res.ok) return;
      const data = await res.json();
      if (data?.results?.length) {
        const top = data.results[0];
        const node = nodes.find((n) => n.id === top.id);
        if (node) await onNodeClick(node);
        else {
          try {
            const d = await api.graphNode(String(top.id));
            if (d && !d.error) setSelected(d);
          } catch { /* ignore */ }
        }
      } else {
        setError(`No entities found matching '${search}'`);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function findPath(e?: React.FormEvent) {
    e?.preventDefault();
    const src = pathSrc.trim() || AUTO_PATH[0];
    const tgt = pathTgt.trim() || AUTO_PATH[1];
    if (!src || !tgt) return;
    try {
      const r = await api.graphPath(src, tgt);
      if (r.error || !r.path) {
        setPathResult(null);
        setError(r.error ?? 'No path found');
        return;
      }
      applyPath({ path: r.path, edges: r.path_edges ?? [], length: r.length ?? r.path.length - 1 }, nodes);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <>
      <Hero title="Knowledge Network" subtitle="Industrial entities and their relationships — equipment, regulations, plants, records" />

      <div className="stat-grid">
        <div className="stat-card"><div className="value">{nodes.length}</div><div className="label">Visible nodes</div></div>
        <div className="stat-card"><div className="value">{links.length}</div><div className="label">Edges</div></div>
        {pathResult && (
          <div className="stat-card" style={{ gridColumn: 'span 2' }}>
            <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>AUTO PATH</div>
            <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--signal-amber)' }}>
              {pathResult.path.join(' → ')}
            </div>
          </div>
        )}
      </div>

      {error && <div className="info-box error">⚠️ {error}</div>}
      {loading && <div className="skeleton" style={{ height: 480 }} />}

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <form onSubmit={doSearch} style={{ display: 'flex', gap: '0.5rem', flex: 1, minWidth: 260 }}>
          <input
            className="input"
            placeholder="Search entity (e.g. PUMP-B01, OISD-117)…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="btn" type="submit">Search</button>
        </form>
        <button className="btn ghost" onClick={() => loadGraph(200)}>⟳ Reload</button>
        <button className="btn ghost" onClick={() => loadGraph(500)}>Load complete network</button>
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: 3, minWidth: 420 }}>
          {!loading && (
            <div ref={containerRef} style={{ border: '1px solid var(--hairline)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', background: 'var(--bg)' }}>
              <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                nodeColor={(n: any) => n.color || '#6366f1'}
                nodeVal={(n: any) => Math.max(Math.sqrt((n as any).degree || 1) * 1.5, 1.5)}
                nodeLabel={(n: any) => `${n.id} (${(n.type || 'unknown').replace('_', ' ').toUpperCase()})`}
                linkLabel={(l: any) => l.relation || ''}
                linkColor={() => 'rgba(77,216,192,0.25)'}
                onNodeClick={onNodeClick}
                backgroundColor="#0B0F14"
                width={width || 760}
                height={560}
              />
            </div>
          )}
        </div>

        <div style={{ flex: 1.4, minWidth: 320 }}>
          <form onSubmit={findPath} className="card">
            <div className="section-title" style={{ marginTop: 0 }}>🔗 Path Finder</div>
            <div className="field">
              <label>From entity</label>
              <input className="input mono" placeholder="e.g. EQ-1002" value={pathSrc} onChange={(e) => setPathSrc(e.target.value)} />
            </div>
            <div className="field">
              <label>To entity</label>
              <input className="input mono" placeholder="e.g. OISD-116" value={pathTgt} onChange={(e) => setPathTgt(e.target.value)} />
            </div>
            <button className="btn" type="submit">Find path</button>
            {pathResult && (
              <div className="info-box success" style={{ marginTop: '0.8rem' }}>
                ✅ {pathResult.length} hop(s):{' '}
                <span className="mono">{pathResult.path.join(' → ')}</span>
              </div>
            )}
          </form>

          {selected && (
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>
                <Tag tone="amber">{selected.id}</Tag>
              </div>
              <div className="metric">
                <span className="k">Type</span>
                <span className="v"><Tag>{TYPE_LABELS[selected.type ?? ''] ?? (selected.type ?? 'unknown')}</Tag></span>
              </div>
              <div className="metric"><span className="k">Degree</span><span className="v">{selected.degree ?? 0}</span></div>
              {selected.doc_id && (
                <div className="metric"><span className="k">Source doc</span><span className="v"><Tag>{selected.doc_id}</Tag></span></div>
              )}
              <div className="divider" />
              <div className="mono" style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>
                Connections
              </div>
              {selected.neighbors?.slice(0, 15).map((nb) => (
                <div className="entity-row" key={nb.id}>
                  <span
                    className="dot"
                    style={{ background: TYPE_COLORS[nb.type ?? ''] ?? '#8394A6' }}
                  />
                  {nb.id}
                  <span className="rel">{nb.relation ?? ''}</span>
                </div>
              ))}
              {!selected.neighbors?.length && (
                <div className="info-box info">No direct connections.</div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
