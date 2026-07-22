'use client';

import { useMemo, useState } from 'react';

import { IssueDrawer } from './IssueDrawer';
import {
  ISSUES,
  ISSUE_COLUMNS,
  PROJECTS,
  formatShortDate,
  type ConstructionIssue,
} from './demo-data';

const HEALTH_TR = {
  on_track: 'Yolunda',
  watch: 'İzle',
  risk: 'Risk',
} as const;

const PRIO_TR: Record<ConstructionIssue['priority'], string> = {
  urgent: 'Acil',
  high: 'Yüksek',
  medium: 'Orta',
  low: 'Düşük',
};

export function ProjectOpsTab() {
  const [projectId, setProjectId] = useState<string>('all');
  const [issues, setIssues] = useState(ISSUES);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [overStatus, setOverStatus] = useState<ConstructionIssue['status'] | null>(null);
  const [selected, setSelected] = useState<ConstructionIssue | null>(null);

  const project = PROJECTS.find((p) => p.id === projectId);

  const scoped = useMemo(
    () => (projectId === 'all' ? issues : issues.filter((i) => i.projectId === projectId)),
    [issues, projectId],
  );

  const byStatus = useMemo(() => {
    const map = {} as Record<ConstructionIssue['status'], ConstructionIssue[]>;
    for (const c of ISSUE_COLUMNS) map[c.id] = [];
    for (const issue of scoped) map[issue.status].push(issue);
    return map;
  }, [scoped]);

  const moveTo = (id: string, status: ConstructionIssue['status']) => {
    setIssues((prev) => prev.map((i) => (i.id === id ? { ...i, status } : i)));
  };

  return (
    <div data-testid="g1-project-ops">
      <div className="g1-preview__toolbar">
        <div className="g1-preview__toolbar-left">
          <div>
            <h2 className="g1-preview__title">Proje Operasyonları</h2>
            <p className="g1-preview__subtitle">
              {project?.name ?? 'Tüm projeler'} · {scoped.length} iş · inşaat kanban (demo)
            </p>
          </div>
        </div>
        <div className="g1-preview__toolbar-right">
          {project ? (
            <>
              <span className={`g1-health g1-health--${project.health}`}>
                {HEALTH_TR[project.health]}
              </span>
              <span className="g1-chip" style={{ cursor: 'default' }}>
                İlerleme %{project.progress}
              </span>
            </>
          ) : (
            <span className="g1-chip" style={{ cursor: 'default' }}>
              {PROJECTS.length} proje · çapraz görünüm
            </span>
          )}
        </div>
      </div>

      <div className="g1-ops">
        <aside className="g1-project-list">
          <div className="g1-project-list__head">Projeler</div>
          <button
            type="button"
            className={`g1-project-item${projectId === 'all' ? ' is-active' : ''}`}
            onClick={() => setProjectId('all')}
          >
            <div className="g1-project-item__row">
              <span className="g1-project-item__name">Tüm projeler</span>
              <span className="g1-health g1-health--on_track">{issues.length}</span>
            </div>
            <div className="g1-project-item__meta">
              <span>Çapraz kanban</span>
              <span>Plane tarzı</span>
            </div>
          </button>
          {PROJECTS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`g1-project-item${p.id === projectId ? ' is-active' : ''}`}
              onClick={() => setProjectId(p.id)}
            >
              <div className="g1-project-item__row">
                <span className="g1-project-item__name">{p.name}</span>
                <span className={`g1-health g1-health--${p.health}`}>{HEALTH_TR[p.health]}</span>
              </div>
              <div className="g1-progress" aria-hidden>
                <i style={{ width: `${p.progress}%` }} />
              </div>
              <div className="g1-project-item__meta">
                <span>
                  {p.phase} · {p.openIssues} açık
                </span>
                <span>{formatShortDate(p.due)}</span>
              </div>
            </button>
          ))}
        </aside>

        <div className="g1-ops__board-wrap">
          <div className="g1-issue-board" role="list">
            {ISSUE_COLUMNS.map((col) => {
              const cards = byStatus[col.id];
              return (
                <section
                  key={col.id}
                  className={`g1-issue-col${overStatus === col.id ? ' g1-issue-col--over' : ''}`}
                  role="listitem"
                  onDragOver={(e) => {
                    e.preventDefault();
                    setOverStatus(col.id);
                  }}
                  onDragLeave={() => setOverStatus((cur) => (cur === col.id ? null : cur))}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (draggingId) moveTo(draggingId, col.id);
                    setDraggingId(null);
                    setOverStatus(null);
                  }}
                >
                  <header className="g1-issue-col__head">
                    <span>{col.labelTr}</span>
                    <span className="g1-col__count">{cards.length}</span>
                  </header>
                  <div className="g1-issue-col__cards">
                    {cards.map((issue) => (
                      <article
                        key={issue.id}
                        className={`g1-issue${draggingId === issue.id ? ' g1-issue--dragging' : ''}`}
                        draggable
                        onDragStart={() => setDraggingId(issue.id)}
                        onDragEnd={() => {
                          setDraggingId(null);
                          setOverStatus(null);
                        }}
                        onClick={() => setSelected(issue)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setSelected(issue);
                          }
                        }}
                        role="button"
                        tabIndex={0}
                        data-testid={`g1-issue-${issue.id}`}
                      >
                        <div className="g1-issue__key">{issue.key}</div>
                        <h3 className="g1-issue__title">{issue.title}</h3>
                        <div className="g1-issue__row">
                          <span className={`g1-prio g1-prio--${issue.priority}`}>
                            {PRIO_TR[issue.priority]}
                          </span>
                          {issue.blockers > 0 ? (
                            <span className="g1-blocker">{issue.blockers} blokör</span>
                          ) : null}
                        </div>
                        <div className="g1-issue__foot">
                          <div className="g1-card__who">
                            <span className="g1-avatar">{issue.initials}</span>
                            <span>{issue.assignee}</span>
                          </div>
                          <span className="g1-card__date">{formatShortDate(issue.due)}</span>
                        </div>
                        {issue.labels.length > 0 ? (
                          <div className="g1-labels" style={{ marginTop: '0.35rem' }}>
                            {issue.labels.slice(0, 2).map((l) => (
                              <span key={l} className="g1-label">
                                {l}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      </div>

      {selected ? <IssueDrawer issue={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
