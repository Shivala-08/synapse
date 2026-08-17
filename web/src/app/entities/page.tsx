'use client';

import { useEffect, useState } from 'react';
import Hero from '@/components/Hero';
import { api } from '@/lib/api';
import { Tag } from '@/components/primitives';
import type { EntitiesResponse, GraphNodeDetail } from '@/lib/types';

const TYPE_COLORS: Record<string, string> = {
  equipment: '#4DD8C0', regulation: '#FFA630', plant: '#34C77B',
  permit: '#f59e0b', work_order: '#8b5cf6', incident: '#ec4899',
  inspection: '#06b6d4', person: '#f97316', hazard: '#E5484D',
  permit_type: '#d97706', incident_type: '#db2777',
};

const TYPE_LABELS: Record<string, string> = {
  equipment: 'Equipment', regulation: 'Regulation', plant: 'Plant / Location',
  permit: 'Permit', work_order: 'Work Order', incident: 'Incident',
  inspection: 'Inspection', person: 'Person', hazard: 'Hazard',
  permit_type: 'Permit Type', incident_type: 'Incident Type',
};

export default function EntitiesPage() {
  const [data, setData] = useState<EntitiesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [type, setType] = useState<string>('equipment');
  const [search, setSearch] = useState('');
  const [relationships, setRelationships] = useState<Record<string, GraphNodeDetail>>({});

  useEffect(() => {
    api
      .entities()
      .then(setData)
      .catch((e) => setError((e as Error).message));
  }, []);

  const types = data ? Object.keys(data.entities).sort() : [];
  const list = (data?.entities[type] ?? []).filter((e) => !search || e.toLowerCase().includes(search.toLowerCase()));

  async function viewRelationships(entityId: string) {
    try {
      const d = await api.graphNode(entityId);
      if (d && !d.error) {
        setRelationships((r) => ({ ...r, [entityId]: d }));
      }
    } catch {
      /* ignore */
    }
  }

  return (
    <>
      <Hero title="Entity Explorer" subtitle="Browse entities extracted from the document corpus" />

      {error && <div className="info-box error">⚠️ {error}</div>}
      {!data && !error && <div className="skeleton" style={{ height: 120 }} />}

      {data && (
        <>
          <div className="stat-grid">
            <div className="stat-card"><div className="value">{data.stats.total_nodes}</div><div className="label">Total nodes</div></div>
            <div className="stat-card"><div className="value">{data.stats.total_edges}</div><div className="label">Edges</div></div>
            <div className="stat-card"><div className="value">{data.stats.density.toFixed(4)}</div><div className="label">Density</div></div>
          </div>

          <div style={{ display: 'flex', gap: '0.8rem', marginBottom: '1.2rem' }}>
            <select className="select" style={{ width: 240 }} value={type} onChange={(e) => setType(e.target.value)}>
              {types.map((t) => (
                <option key={t} value={t}>{TYPE_LABELS[t] ?? t.replace('_', ' ')} ({data.entities[t].length})</option>
              ))}
            </select>
            <input
              className="input"
              placeholder="Search entities…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="info-box info" style={{ marginBottom: '1rem' }}>
            {list.length} {TYPE_LABELS[type] ?? type} entities
          </div>

          {list.slice(0, 100).map((eid) => {
            const rel = relationships[eid];
            return (
              <div key={eid}>
                <div className="entity-row" style={{ justifyContent: 'space-between' }}>
                  <span>
                    <span
                      className="dot"
                      style={{ background: TYPE_COLORS[type] ?? '#8394A6', marginRight: '0.5rem' }}
                    />
                    <Tag tone="cyan">{eid}</Tag>
                  </span>
                  <button className="btn ghost" style={{ padding: '0.25rem 0.7rem', fontSize: '0.75rem' }} onClick={() => viewRelationships(eid)}>
                    {rel ? 'Hide' : 'Relationships'}
                  </button>
                </div>
                {rel && (
                  <details className="expander" open>
                    <summary>Relationships — {eid}</summary>
                    <div className="expander-body">
                      <div className="metric"><span className="k">Type</span><span className="v">{rel.type ?? 'unknown'}</span></div>
                      <div className="metric"><span className="k">Degree</span><span className="v">{rel.degree ?? 0}</span></div>
                      {rel.neighbors?.slice(0, 20).map((nb) => (
                        <div className="entity-row" key={nb.id}>
                          <span className="dot" style={{ background: TYPE_COLORS[nb.type ?? ''] ?? '#6b7280' }} />
                          {nb.id}
                          <span className="rel">{nb.relation ?? ''}</span>
                        </div>
                      ))}
                      {!rel.neighbors?.length && <div className="info-box info">No direct connections.</div>}
                    </div>
                  </details>
                )}
              </div>
            );
          })}

          {list.length > 100 && (
            <div className="info-box info">Showing first 100 of {list.length} entities.</div>
          )}
        </>
      )}
    </>
  );
}
