'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { useDomain, toSegment } from '@/lib/DomainContext';
import type { MasteryResponse } from '@/lib/types';

interface Activity {
  t: number;
  entities: string[];
}

function readActivity(domainId: string): Activity[] {
  try {
    return JSON.parse(localStorage.getItem(`synapse_activity_${domainId}`) || '[]');
  } catch {
    return [];
  }
}

function buildRows(data: MasteryResponse, activity: Activity[]) {
  const subjects = [...data.subjects].sort((a, b) => a.mastery_pct - b.mastery_pct);
  return subjects.map((s) => {
    const ids = new Set(s.entity_ids);
    const hits = activity.filter((a) => a.entities.some((e) => ids.has(e)));
    const last = hits.length ? Math.max(...hits.map((h) => h.t)) : null;
    return { subject: s, queried: hits.length, last };
  });
}

/** Amber (low mastery) to teal (high mastery) as a smooth hue blend. */
function barColor(pct: number): string {
  const hue = 30 + (pct / 100) * 140;
  return `hsl(${hue} 72% 62%)`;
}

function relTime(t: number): string {
  const days = Math.floor((Date.now() - t) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  return new Date(t).toLocaleDateString();
}

const RING_R = 84;
const RING_C = 2 * Math.PI * RING_R;

export default function RevisionPage() {
  const params = useParams<{ domain: string }>();
  const segment = params.domain ?? '';
  const { resolve } = useDomain();
  const domain = resolve(segment);
  const domainId = domain?.domain_id;

  const [data, setData] = useState<MasteryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [ringOn, setRingOn] = useState(false);

  useEffect(() => {
    if (!domainId) return;
    let mounted = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const m = await api.mastery(domainId);
        if (mounted) setData(m);
      } catch (e) {
        if (mounted) setError((e as Error).message);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [domainId]);

  // One-time ring fill on first load (never repeats).
  useEffect(() => {
    const t = setTimeout(() => setRingOn(true), 120);
    return () => clearTimeout(t);
  }, [loading]);

  // Small, per-render computation: a handful of subjects and a local activity
  // log that only changes via this app's own query writes.
  const rows = data && domainId ? buildRows(data, readActivity(domainId)) : [];

  if (!domain) return <div className="skeleton" style={{ height: 240 }} />;

  return (
    <>
      <div className="page-head">
        <h1 className="page-title">Revision dashboard</h1>
        <p className="page-sub">
          What you know across {domain.display_name}, weakest topics first.
          Mastery is estimated from how well each topic&apos;s entities are linked
          into the knowledge graph.
        </p>
      </div>

      {error && <div className="info-box error">{error}</div>}

      {loading && !data ? (
        <>
          <div className="skeleton" style={{ width: 210, height: 210, borderRadius: '50%', marginBottom: '1.5rem' }} />
          <div className="skeleton" style={{ height: 52, marginBottom: '0.6rem' }} />
          <div className="skeleton" style={{ height: 52, marginBottom: '0.6rem' }} />
          <div className="skeleton" style={{ height: 52 }} />
        </>
      ) : data && data.subjects.length === 0 ? (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>Nothing tracked yet</div>
          <p style={{ color: 'var(--text-muted)', maxWidth: '60ch' }}>
            Mastery appears here once topics have entities linked into the
            knowledge graph. Ingest sources for this domain and query the
            corpus; each query also records which topics you reviewed.
          </p>
        </div>
      ) : data ? (
        <>
          <div className="ring-hero">
            <svg viewBox="0 0 200 200" width={210} height={210} role="img" aria-label={`Overall mastery ${data.overall_pct} percent`}>
              <circle cx="100" cy="100" r={RING_R} fill="none" stroke="var(--border)" strokeWidth="12" />
              <circle
                className="ring-fill"
                cx="100" cy="100" r={RING_R}
                fill="none"
                stroke={barColor(data.overall_pct)}
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={RING_C}
                strokeDashoffset={ringOn ? RING_C * (1 - data.overall_pct / 100) : RING_C}
                transform="rotate(-90 100 100)"
              />
            </svg>
            <div className="ring-center">
              <div className="ring-value">{data.overall_pct}%</div>
              <div className="ring-label">overall mastery</div>
            </div>
          </div>
          <div className="ring-meta">
            <span>{data.subjects.length} topics</span>
            <span className="ring-meta-dot" aria-hidden />
            <span>
              {data.subjects.reduce((n, s) => n + s.total, 0)} entities in the graph
            </span>
          </div>

          <div className="section-title">Weakest first</div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {rows.map(({ subject, queried, last }) => (
              <div className="rev-row" key={subject.name}>
                <div className="rev-info">
                  <div className="rev-name">{subject.name}</div>
                  <div className="rev-meta">
                    <span>{last ? `reviewed ${relTime(last)}` : 'not reviewed yet'}</span>
                    <span>{queried} quer{queried === 1 ? 'y' : 'ies'}</span>
                  </div>
                </div>
                <div className="rev-bar-wrap">
                  <div
                    className="rev-bar"
                    style={{
                      width: `${Math.max(subject.mastery_pct, 2)}%`,
                      background: barColor(subject.mastery_pct),
                      opacity: subject.mastery_pct === 0 ? 0.55 : 1,
                    }}
                  />
                </div>
                <div className="rev-pct mono">{subject.mastery_pct}%</div>
                <Link
                  className="btn ghost"
                  href={`/${toSegment(domain.domain_id)}/query?topic=${encodeURIComponent(subject.name)}`}
                >
                  Query this topic
                </Link>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}