'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { MagnifyingGlass, ArrowsClockwise, Path, X } from '@phosphor-icons/react';
import { api, API_URL } from '@/lib/api';
import { useDomain } from '@/lib/DomainContext';
import { Tag } from '@/components/primitives';
import type { GraphEdge, GraphNodeDetail } from '@/lib/types';
import type { ForceGraphMethods, LinkObject, NodeObject } from 'react-force-graph-2d';

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

// A small palette derived from the signal indigo at varying brightness.
// One hue family, opacity/brightness carries the type distinction.
const TYPE_COLORS: Record<string, string> = {
  equipment: '#7C9EFF', regulation: '#A5BEFF', plant: '#5B7FEA',
  permit: '#93ADF7', work_order: '#6C8FEF', incident: '#B9CCFF',
  inspection: '#8AA6F9', person: '#6488EC', hazard: '#7C9EFF',
  permit_type: '#9FB7FA', incident_type: '#A9C0FC',
  DatabaseConcept: '#7C9EFF', SQLCommand: '#A5BEFF', ProgrammingLanguage: '#5B7FEA',
  Framework: '#8AA6F9', APIEndpoint: '#6C8FEF', TechStack: '#B9CCFF',
  Project: '#7C9EFF', BugFix: '#A5BEFF', Decision: '#5B7FEA',
  APIIntegration: '#8AA6F9',
};

const FALLBACK_COLOR = '#8394A6';

function degreesOf(links: FGLink[]): Record<string, number> {
  const deg: Record<string, number> = {};
  links.forEach((l) => {
    const s = String(l.source);
    const t = String(l.target);
    deg[s] = (deg[s] || 0) + 1;
    deg[t] = (deg[t] || 0) + 1;
  });
  return deg;
}

/** Domain-neutral stand-in for the old hardcoded EQ/OISD auto path. */
function topTwo(links: FGLink[]): [string | undefined, string | undefined] {
  const deg = degreesOf(links);
  const sorted = Object.entries(deg).sort((a, b) => b[1] - a[1]);
  return [sorted[0]?.[0], sorted[1]?.[0]];
}

export default function GraphPage() {
  const params = useParams<{ domain: string }>();
  const segment = params.domain ?? '';
  const { resolve } = useDomain();
  const domain = resolve(segment);
  const domainId = domain?.domain_id;

  const [nodes, setNodes] = useState<FGNode[]>([]);
  const [links, setLinks] = useState<FGLink[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<GraphNodeDetail | null>(null);
  const [search, setSearch] = useState('');
  const [pathSrc, setPathSrc] = useState('');
  const [pathTgt, setPathTgt] = useState('');
  const [pathResult, setPathResult] = useState<{ path: string[]; edges: GraphEdge[]; length: number } | null>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const graphRef = useRef<ForceGraphMethods<NodeObject, LinkObject> | undefined>(undefined);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const pendingNode = useRef<string | null>(null);

  // ?node=<id> deep link from the query console source chips
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const n = q.get('node');
    if (n) pendingNode.current = n;
  }, []);

  const measure = useCallback(() => {
    if (!wrapRef.current) return;
    setDims({ width: wrapRef.current.clientWidth, height: wrapRef.current.clientHeight });
  }, []);

  useEffect(() => {
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [measure]);

  function applyPath(r: { path: string[]; edges: GraphEdge[]; length: number }, visible: FGNode[]) {
    const pathSet = new Set(r.path);
    setNodes(visible.filter((n) => pathSet.has(n.id)));
    setLinks((r.edges ?? []).map((e) => ({ source: e.from, target: e.to, relation: e.relation })));
    setPathResult(r);
  }

  async function loadGraph(maxNodes: number) {
    if (!domainId) return;
    setLoading(true);
    setError(null);
    try {
      const g = await api.graph(maxNodes, domainId);
      setNodes(g.nodes.map((n) => ({
        id: n.id,
        type: n.type,
        color: n.color || TYPE_COLORS[n.type ?? ''] || FALLBACK_COLOR,
        val: 1,
      })));
      setLinks(g.edges.map((e) => ({ source: e.from, target: e.to, relation: e.relation })));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // Load the full graph, then a representative traversal between the two
  // most connected nodes. Never fails the page if entities are absent.
  useEffect(() => {
    if (!domainId) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const g = await api.graph(200, domainId);
        const mappedLinks: FGLink[] = g.edges.map((e) => ({ source: e.from, target: e.to, relation: e.relation }));
        const mappedNodes: FGNode[] = g.nodes.map((n) => ({
          id: n.id,
          type: n.type,
          color: n.color || TYPE_COLORS[n.type ?? ''] || FALLBACK_COLOR,
          val: 1,
        }));
        setNodes(mappedNodes);
        setLinks(mappedLinks);

        const [a, b] = topTwo(mappedLinks);
        if (a && b) {
          try {
            const r = await api.graphPath(a, b, domainId);
            if (r && !r.error && r.path && r.path.length > 1) {
              applyPath({ path: r.path, edges: r.path_edges ?? [], length: r.length ?? r.path.length - 1 }, mappedNodes);
            }
          } catch { /* fall back to full graph */ }
        }

        // Honor a ?node deep link once the graph is in place
        const want = pendingNode.current;
        if (want) {
          pendingNode.current = null;
          const hit = mappedNodes.find((n) => n.id === want);
          if (hit) {
            await onNodeClick(hit, domainId);
          } else {
            setInfo(`No node '${want}' in this domain's graph.`);
          }
        }
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domainId]);

  const graphData = useMemo(() => ({ nodes, links }), [nodes, links]);
  const degree = useMemo(() => degreesOf(links), [links]);

  async function onNodeClick(node: NodeObject, did?: string) {
    try {
      const d = await api.graphNode(String(node.id), did ?? domainId);
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
    if (!search.trim() || !domainId) return;
    setError(null);
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
            const d = await api.graphNode(String(top.id), domainId);
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
    if (!domainId) return;
    const src = pathSrc.trim();
    const tgt = pathTgt.trim();
    if (!src || !tgt) return;
    setError(null);
    try {
      const r = await api.graphPath(src, tgt, domainId);
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

  if (!domain) {
    return <div className="skeleton" style={{ height: '100dvh' }} />;
  }

  return (
    <div className="graph-canvas-wrap" ref={wrapRef}>
      <div className="graph-overlay">
        <form onSubmit={doSearch} className="graph-search">
          <input
            className="input"
            placeholder="Search a node..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="btn" type="submit" aria-label="Search">
            <MagnifyingGlass size={15} />
          </button>
        </form>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button className="btn ghost" onClick={() => loadGraph(200)}>
            <ArrowsClockwise size={13} style={{ marginRight: '0.3rem', verticalAlign: '-2px' }} />
            Reload
          </button>
          <button className="btn ghost" onClick={() => loadGraph(500)}>
            Complete network
          </button>
        </div>

        <div className="panel" style={{ padding: '0.8rem 1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
            <Path size={14} color="var(--signal)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Path finder</span>
          </div>
          <form onSubmit={findPath} style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <input
              className="input mono"
              placeholder="From node"
              value={pathSrc}
              onChange={(e) => setPathSrc(e.target.value)}
            />
            <input
              className="input mono"
              placeholder="To node"
              value={pathTgt}
              onChange={(e) => setPathTgt(e.target.value)}
            />
            <button className="btn" type="submit" style={{ padding: '0.4rem 0.9rem', fontSize: '0.8rem' }}>
              Find path
            </button>
          </form>
          {pathResult && (
            <div className="info-box success" style={{ margin: '0.6rem 0 0', fontSize: '0.76rem' }}>
              {pathResult.length} hop{pathResult.length === 1 ? '' : 's'}:{' '}
              <span className="mono">{pathResult.path.join(' -> ')}</span>
            </div>
          )}
        </div>

        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'flex', gap: '0.8rem' }}>
          <span>{nodes.length} nodes</span>
          <span>{links.length} edges</span>
        </div>
      </div>

      {error && (
        <div className="info-box error" style={{ position: 'absolute', top: '1.2rem', left: '50%', transform: 'translateX(-50%)', zIndex: 6, margin: 0 }}>
          {error}
        </div>
      )}
      {info && (
        <div className="info-box info" style={{ position: 'absolute', top: '1.2rem', left: '50%', transform: 'translateX(-50%)', zIndex: 6, margin: 0 }}>
          {info}
        </div>
      )}

      {loading ? (
        <div className="skeleton" style={{ height: '100%', borderRadius: 0 }} />
      ) : (
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeColor={(n) => n.color || FALLBACK_COLOR}
          nodeVal={(n) => {
            const d = n.id != null ? degree[String(n.id)] ?? 1 : 1;
            return Math.max(Math.sqrt(Number(d)) * 1.5, 1.5);
          }}
          nodeLabel={(n) => `${n.id} (${(n.type || 'unknown').replace('_', ' ').toLowerCase()})`}
          linkLabel={(l) => l.relation || ''}
          linkColor={() => 'rgba(124, 158, 255, 0.25)'}
          onNodeClick={(n) => onNodeClick(n)}
          backgroundColor="#0B0E13"
          width={dims.width || 800}
          height={dims.height || 600}
        />
      )}

      {selected && (
        <div className="graph-side-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
            <Tag tone="signal">{selected.id}</Tag>
            <button
              className="btn ghost"
              onClick={() => setSelected(null)}
              style={{ padding: '0.25rem 0.5rem' }}
              aria-label="Close panel"
            >
              <X size={14} />
            </button>
          </div>
          <div className="metric" style={{ marginTop: '0.6rem' }}>
            <span className="k">Type</span>
            <span className="v">{selected.type ?? 'unknown'}</span>
          </div>
          <div className="metric">
            <span className="k">Degree</span>
            <span className="v">{selected.degree ?? 0}</span>
          </div>
          {selected.doc_id && (
            <div className="metric">
              <span className="k">Source doc</span>
              <span className="v">{selected.doc_id}</span>
            </div>
          )}
          <div className="divider" />
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Connections</div>
          {selected.neighbors?.slice(0, 20).map((nb) => (
            <div className="entity-row" key={nb.id}>
              <span className="dot" style={{ background: TYPE_COLORS[nb.type ?? ''] ?? FALLBACK_COLOR }} />
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
  );
}