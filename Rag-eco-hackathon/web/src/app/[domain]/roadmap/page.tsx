'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { ArrowsClockwise } from '@phosphor-icons/react';
import { api } from '@/lib/api';
import { useDomain } from '@/lib/DomainContext';
import type { RoadmapBlock, RoadmapPlan } from '@/lib/types';

// Small signal-derived indigo family, consistent with the graph palette.
const PALETTE = ['#7C9EFF', '#A5BEFF', '#5B7FEA', '#8AA6F9', '#6C8FEF', '#B9CCFF', '#93ADF7', '#6488EC'];

function subjectColor(subject: string): string {
  let h = 0;
  for (const ch of subject) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

export default function RoadmapPage() {
  const params = useParams<{ domain: string }>();
  const { resolve } = useDomain();
  const domain = resolve(params.domain ?? '');
  const domainId = domain?.domain_id;

  const [plan, setPlan] = useState<RoadmapPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [examDate, setExamDate] = useState('');
  const [dailyHours, setDailyHours] = useState(2);
  const [dateHint, setDateHint] = useState(false);
  const [hover, setHover] = useState<{ x: number; y: number; block: RoadmapBlock } | null>(null);

  // Restore persisted inputs (deferred so no state updates run synchronously
  // inside the effect body). A ?exam=YYYY-MM-DD query param takes precedence
  // and is persisted, so plans are shareable as deep links.
  useEffect(() => {
    if (!domainId) return;
    const t = setTimeout(() => {
      try {
        const q = new URLSearchParams(window.location.search);
        const fromUrl = q.get('exam');
        if (fromUrl && /^\d{4}-\d{2}-\d{2}$/.test(fromUrl)) {
          setExamDate(fromUrl);
          localStorage.setItem(`synapse_exam_${domainId}`, fromUrl);
        } else {
          const d = localStorage.getItem(`synapse_exam_${domainId}`);
          if (d) setExamDate(d);
        }
        const h = localStorage.getItem(`synapse_hours_${domainId}`);
        if (h) setDailyHours(Number(h) || 2);
      } catch { /* ignore */ }
    }, 0);
    return () => clearTimeout(t);
  }, [domainId]);

  const loadPlan = useCallback(async (date: string, hours: number) => {
    if (!domainId) return;
    setLoading(true);
    setError(null);
    try {
      const p = await api.roadmapPlan(domainId, date || null, hours);
      setPlan(p);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [domainId]);

  // Auto-generate once persisted inputs are restored, if a date exists.
  // No ref guard: the cleanup clears the pending timeout, so StrictMode's
  // double-mount in dev fires the plan request exactly once.
  useEffect(() => {
    if (!domainId) return;
    const t = setTimeout(() => {
      try {
        const q = new URLSearchParams(window.location.search);
        const fromUrl = q.get('exam');
        const d =
          fromUrl && /^\d{4}-\d{2}-\d{2}$/.test(fromUrl)
            ? fromUrl
            : localStorage.getItem(`synapse_exam_${domainId}`);
        if (d) {
          const h = Number(localStorage.getItem(`synapse_hours_${domainId}`)) || 2;
          loadPlan(d, h);
        }
      } catch { /* ignore */ }
    }, 0);
    return () => clearTimeout(t);
  }, [domainId, loadPlan]);

  const saveAndGenerate = () => {
    if (!domainId) return;
    if (!examDate) {
      setDateHint(true);
      return;
    }
    setDateHint(false);
    localStorage.setItem(`synapse_exam_${domainId}`, examDate);
    localStorage.setItem(`synapse_hours_${domainId}`, String(dailyHours));
    loadPlan(examDate, dailyHours);
  };

  if (!domain) return <div className="skeleton" style={{ height: 240 }} />;

  const totalHours = plan && plan.exam_date ? Math.round(plan.days_remaining * plan.daily_hours) : null;

  return (
    <>
      <div className="page-head page-head-row">
        <div>
          <h1 className="page-title">Roadmap</h1>
          <p className="page-sub">
            A day-by-day plan to your exam date, weighted toward your weakest
            topics. Hours are allocations, not logged study time.
          </p>
        </div>
        <div className="roadmap-controls">
          <label className="rm-field">
            <span>Exam date</span>
            <input type="date" className="input" value={examDate} onChange={(e) => { setExamDate(e.target.value); setDateHint(false); }} />
          </label>
          <label className="rm-field">
            <span>Hours per day</span>
            <input
              type="number"
              className="input"
              min={0.5}
              max={12}
              step={0.5}
              value={dailyHours}
              onChange={(e) => setDailyHours(Number(e.target.value) || 2)}
            />
          </label>
          <button className="btn" onClick={saveAndGenerate} disabled={loading}>
            <ArrowsClockwise size={14} style={{ marginRight: '0.35rem', verticalAlign: '-2px' }} />
            Regenerate
          </button>
        </div>
      </div>

      {error && <div className="info-box error">{error}</div>}
      {dateHint && (
        <div className="info-box warning">Pick an exam date to generate the plan.</div>
      )}

      {loading ? (
        <div className="skeleton" style={{ height: 260 }} />
      ) : !plan || plan.days.length === 0 ? (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>
            {plan?.note && plan.note.includes('No topics') ? 'Nothing to plan yet' : 'Set your exam date'}
          </div>
          <p style={{ color: 'var(--text-muted)', maxWidth: '62ch' }}>
            {plan?.note && plan.note.includes('No topics')
              ? 'Topics appear here once this domain has entities linked into the knowledge graph. Ingest sources first, then regenerate.'
              : 'The timeline renders from today to your exam date, with each day split across topics by need. Pick a date and regenerate.'}
          </p>
        </div>
      ) : (
        <>
          <div className="roadmap-stats">
            {plan.exam_date ? (
              <span>{plan.days_remaining} days to exam</span>
            ) : (
              <span>{plan.days_remaining}-day horizon</span>
            )}
            {totalHours != null && <span>{totalHours} hours planned</span>}
            <span>{plan.subjects.length} topics</span>
            {plan.shown_days < plan.days_remaining && (
              <span style={{ color: 'var(--text-dim)' }}>showing the first {plan.shown_days} of {plan.days_remaining} days</span>
            )}
          </div>

          {/* Legend: block colour per subject, so the timeline reads at a glance. */}
          <div className="roadmap-legend">
            {plan.subjects.map((s) => (
              <span className="rm-legend-item" key={s.name}>
                <span className="rm-legend-swatch" style={{ background: subjectColor(s.name) }} />
                {s.name}
                <span className="rm-legend-pct mono">{s.mastery_pct}%</span>
              </span>
            ))}
          </div>

          {/* Day cells annotated with month boundaries so a long plan is scannable. */}
          <div className="roadmap-scroll">
            <div className="rm-track">
              {plan.days.map((d, i) => {
                const isWeekend = d.weekday === 'Sat' || d.weekday === 'Sun';
                const prev = i > 0 ? plan.days[i - 1] : null;
                const monthStart = !prev || prev.month !== d.month;
                return (
                  <div
                    className={`rm-day ${i === 0 ? 'today' : ''} ${isWeekend ? 'weekend' : ''}`}
                    key={d.date}
                  >
                    <div className="rm-day-head">
                      {monthStart && <span className="rm-month">{d.month}</span>}
                      {i === 0 && <span className="rm-today-tag">Today</span>}
                    </div>
                    <div className="rm-blocks">
                      {d.blocks.map((b) => (
                        <div
                          key={b.subject}
                          className="rm-block"
                          style={{
                            height: `${Math.max((b.hours / plan.daily_hours) * 150, 6)}px`,
                            background: subjectColor(b.subject),
                          }}
                          onMouseEnter={(e) => setHover({ x: e.clientX, y: e.clientY, block: b })}
                          onMouseMove={(e) => setHover({ x: e.clientX, y: e.clientY, block: b })}
                          onMouseLeave={() => setHover(null)}
                        />
                      ))}
                    </div>
                    <div className="rm-daynum">{d.day}</div>
                    <div className="rm-wd">{d.weekday}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {hover && (
            <div className="rm-tooltip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
              <div className="rm-tt-subject">{hover.block.subject}</div>
              <div>{hover.block.hours} hours</div>
              <div>priority {hover.block.priority}/10</div>
              <div>mastery {hover.block.mastery_pct}%</div>
            </div>
          )}
        </>
      )}
    </>
  );
}