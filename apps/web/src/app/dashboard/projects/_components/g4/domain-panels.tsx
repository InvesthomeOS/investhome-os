'use client';

import { useEffect, useMemo, useState } from 'react';

import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import { BarChart, LineChart, Sparkline } from '@/components/design-system/charts';
import {
  fetchBudgetSummary,
  fetchProjectCommitments,
  fetchRecentProjectActivity,
  fetchUpcomingMilestones,
  formatCurrency,
  type Project,
  type ProjectActivityItem,
  type ProjectCommitment,
  type ProjectMilestoneItem,
} from '@/lib/api/projects';

import type {
  ChangeOrderLocal,
  InspectionRecord,
  MilestoneRecord,
  PermitRecord,
  RiskRecord,
} from './construction-domain';
import {
  addCustomMilestone,
  listInspections,
  listLocalChangeOrders,
  listMilestonesForProject,
  listPermits,
  listRisks,
  updateMilestoneStatus,
} from './ops-store';
import {
  PORTFOLIO_TYPE_META,
  projectCompletion,
  projectValue,
  toPortfolioType,
  type ProjectPortfolioType,
} from './project-types';

function lab(labels: Record<string, string>, key: string): string {
  return labels[key] ?? key;
}

function DataTag({ kind, label }: { kind: 'live' | 'partial' | 'demo' | 'blocked'; label: string }) {
  return <span className={`proj-g4__data-tag proj-g4__data-tag--${kind}`}>{label}</span>;
}

interface DomainCommon {
  projects: Project[];
  locale: string;
  labels: Record<string, string>;
  typeLabel: (t: ProjectPortfolioType) => string;
  selectedProjectId: string | null;
}

export function AnalyticsStrip({
  projects,
  locale,
  labels,
  typeLabel,
  compact = false,
}: DomainCommon & { compact?: boolean }) {
  const total = projects.length;
  const active = projects.filter((p) => !['completed', 'cancelled', 'on_hold'].includes(p.project_status)).length;
  const construction = projects.filter((p) => toPortfolioType(p) === 'construction' || p.project_status === 'construction').length;
  const portfolioValue = projects.reduce((s, p) => s + projectValue(p), 0);
  const avgCompletion =
    total === 0 ? 0 : Math.round(projects.reduce((s, p) => s + projectCompletion(p), 0) / total);

  const typeBars = PORTFOLIO_TYPE_META.filter((t) => !['cancelled', 'on_hold'].includes(t.id))
    .slice(0, 8)
    .map((t) => ({
      label: typeLabel(t.id).slice(0, 10),
      value: projects.filter((p) => toPortfolioType(p) === t.id).length,
    }));

  const trend = [0.65, 0.72, 0.78, 0.84, 0.9, 0.95, 1].map((f, idx) => ({
    label: `T${idx + 1}`,
    value: Math.round(portfolioValue * f),
  }));

  const sparkValue = trend.map((p) => p.value / 1_000_000 || 0.1);
  const sparkActive = [active * 0.7, active * 0.8, active * 0.85, active * 0.9, active * 0.95, active || 1];

  const kpis = [
    { key: 'total', label: lab(labels, 'kpiTotal'), value: String(total), spark: sparkActive },
    { key: 'active', label: lab(labels, 'kpiActive'), value: String(active), spark: sparkActive },
    { key: 'construction', label: lab(labels, 'kpiConstruction'), value: String(construction), spark: sparkActive },
    {
      key: 'value',
      label: lab(labels, 'kpiValue'),
      value: formatCurrency(String(portfolioValue), locale),
      spark: sparkValue,
    },
    { key: 'completion', label: lab(labels, 'kpiCompletion'), value: `${avgCompletion}%`, spark: sparkActive },
  ];

  return (
    <div data-testid="proj-g4-analytics">
      <div className="proj-g4__kpis">
        {kpis.map((kpi) => (
          <div key={kpi.key} className="proj-g4__kpi">
            <p>{kpi.label}</p>
            <strong>{kpi.value}</strong>
            <div className="proj-g4__kpi-spark">
              <Sparkline values={kpi.spark} ariaLabel={kpi.label} locale={locale} />
            </div>
          </div>
        ))}
      </div>
      {!compact ? (
        <div className="proj-g4__charts" style={{ marginTop: '0.65rem' }}>
          <div className="proj-g4__chart-card">
            <h4>{lab(labels, 'chartTypeDist')}</h4>
            <BarChart data={typeBars} ariaLabel={lab(labels, 'chartTypeDist')} locale={locale} />
          </div>
          <div className="proj-g4__chart-card">
            <h4>{lab(labels, 'chartValueTrend')}</h4>
            <LineChart
              data={trend}
              ariaLabel={lab(labels, 'chartValueTrend')}
              locale={locale}
              format="compact"
              height={140}
            />
          </div>
        </div>
      ) : null}
      <p className="proj-g4__banner proj-g4__banner--gap" style={{ marginTop: '0.55rem' }}>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} /> {lab(labels, 'analyticsNote')}
      </p>
    </div>
  );
}

export function TasksListPanel({
  tasks,
  labels,
  onOpen,
}: {
  tasks: { id: string; key: string; title: string; projectName: string; stage: string; priority: string; dueDate: string | null }[];
  labels: Record<string, string>;
  onOpen: (id: string) => void;
}) {
  return (
    <div className="proj-g4__panel" data-testid="proj-g4-tasks">
      <h3>{lab(labels, 'tasksTitle')}</h3>
      <p>
        <DataTag kind="demo" label={lab(labels, 'demoTag')} /> {lab(labels, 'tasksGap')}
      </p>
      <div className="proj-g4__list-wrap">
        <table className="proj-g4__table">
          <thead>
            <tr>
              <th>Key</th>
              <th>{lab(labels, 'title')}</th>
              <th>{lab(labels, 'project')}</th>
              <th>{lab(labels, 'stage')}</th>
              <th>{lab(labels, 'priority')}</th>
              <th>{lab(labels, 'due')}</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id} onClick={() => onOpen(task.id)} tabIndex={0}>
                <td>{task.key}</td>
                <td>
                  <strong>{task.title}</strong>
                </td>
                <td>{task.projectName}</td>
                <td>{task.stage}</td>
                <td>{task.priority}</td>
                <td>{task.dueDate ?? 'â€”'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function TimelinePanel({ projects, locale, labels }: DomainCommon) {
  const [activity, setActivity] = useState<ProjectActivityItem[]>([]);
  const [milestones, setMilestones] = useState<ProjectMilestoneItem[]>([]);

  useEffect(() => {
    void (async () => {
      try {
        const [act, ms] = await Promise.all([
          fetchRecentProjectActivity({ limit: 40 }),
          fetchUpcomingMilestones({ days: 120 }),
        ]);
        setActivity(act.items);
        setMilestones(ms.items);
      } catch {
        setActivity([]);
        setMilestones([]);
      }
    })();
  }, []);

  const items = useMemo(() => {
    const rows: { id: string; title: string; meta: string; at: string }[] = [];
    for (const a of activity) {
      rows.push({
        id: `a-${a.id}`,
        title: a.title,
        meta: `${a.project_name ?? ''} Â· ${a.type}`,
        at: a.created_at,
      });
    }
    for (const m of milestones) {
      rows.push({
        id: `m-${m.id}`,
        title: m.title,
        meta: `${m.project_name ?? ''} Â· milestone`,
        at: m.date ?? '',
      });
    }
    return rows.sort((a, b) => b.at.localeCompare(a.at)).slice(0, 40);
  }, [activity, milestones]);

  return (
    <div className="proj-g4__panel" data-testid="proj-g4-timeline">
      <h3>{lab(labels, 'timelineTitle')}</h3>
      <p>
        <DataTag kind="live" label={lab(labels, 'liveTag')} /> {lab(labels, 'timelineHint')}
      </p>
      <div className="proj-g4__timeline">
        {items.length === 0 ? (
          <div className="proj-g4__empty">{lab(labels, 'empty')}</div>
        ) : (
          items.map((item) => (
            <div key={item.id} className="proj-g4__timeline-item">
              <strong>{item.title}</strong>
              <span>
                {item.meta} Â· {item.at ? new Date(item.at).toLocaleDateString(locale) : 'â€”'}
              </span>
            </div>
          ))
        )}
      </div>
      <p style={{ display: 'none' }}>{projects.length}</p>
    </div>
  );
}

export function MilestonesPanel({ projects, labels, selectedProjectId }: DomainCommon) {
  const project = projects.find((p) => p.id === selectedProjectId) ?? projects[0];
  const [items, setItems] = useState<MilestoneRecord[]>([]);
  const [custom, setCustom] = useState('');

  useEffect(() => {
    if (!project) return;
    setItems(listMilestonesForProject(project.id, project.project_name));
  }, [project]);

  if (!project) {
    return <div className="proj-g4__empty">{lab(labels, 'empty')}</div>;
  }

  return (
    <div className="proj-g4__panel" data-testid="proj-g4-milestones">
      <h3>
        {lab(labels, 'milestonesTitle')} — {project.project_name}
      </h3>
      <p>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} /> {lab(labels, 'milestonesGap')}
      </p>
      <div className="proj-g4__list-wrap">
        <table className="proj-g4__table">
          <thead>
            <tr>
              <th>#</th>
              <th>{lab(labels, 'title')}</th>
              <th>{lab(labels, 'status')}</th>
              <th>{lab(labels, 'actions')}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id}>
                <td>{m.order}</td>
                <td>{lab(labels, `ms_${m.key}`) || m.title}</td>
                <td>{lab(labels, `msStatus_${m.status}`) || m.status}</td>
                <td>
                  <select
                    value={m.status}
                    onChange={(e) => {
                      updateMilestoneStatus(m.id, e.target.value as MilestoneRecord['status']);
                      setItems(listMilestonesForProject(project.id));
                    }}
                  >
                    {(['not_started', 'in_progress', 'at_risk', 'completed', 'skipped'] as const).map(
                      (s) => (
                        <option key={s} value={s}>
                          {labels[`msStatus_${s}`] ?? s}
                        </option>
                      ),
                    )}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="proj-g4__toolbar" style={{ marginTop: '0.55rem' }}>
        <input
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          placeholder={lab(labels, 'customMilestone')}
          style={{ flex: 1, padding: '0.35rem 0.5rem', border: '1px solid var(--proj-border)', borderRadius: 6 }}
        />
        <button
          type="button"
          className="proj-g4__btn proj-g4__btn--primary"
          onClick={() => {
            if (!custom.trim()) return;
            addCustomMilestone(project.id, custom.trim());
            setCustom('');
            setItems(listMilestonesForProject(project.id));
          }}
        >
          {lab(labels, 'add')}
        </button>
      </div>
    </div>
  );
}

export function BudgetPanel({ projects, locale, labels, selectedProjectId }: DomainCommon) {
  const project = projects.find((p) => p.id === selectedProjectId) ?? projects[0];
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof fetchBudgetSummary>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!project) return;
    void (async () => {
      try {
        setSummary(await fetchBudgetSummary(project.id));
        setError(null);
      } catch {
        setSummary(null);
        setError(lab(labels, 'budgetLoadError'));
      }
    })();
  }, [project, labels]);

  if (!project) return <div className="proj-g4__empty">{lab(labels, 'empty')}</div>;

  return (
    <div className="proj-g4__panel" data-testid="proj-g4-budget">
      <h3>
        {lab(labels, 'budgetTitle')} — {project.project_name}
      </h3>
      <p>
        <DataTag kind="live" label={lab(labels, 'liveTag')} /> {lab(labels, 'budgetHint')}
      </p>
      {error ? <p className="proj-g4__banner">{error}</p> : null}
      {summary ? (
        <>
          <div className="proj-g4__kpis">
            {Object.entries(summary.totals)
              .slice(0, 4)
              .map(([key, metric]) => (
                <div key={key} className="proj-g4__kpi">
                  <p>{key}</p>
                  <strong>
                    {formatCurrency(String(metric.value ?? 0), locale)}
                  </strong>
                </div>
              ))}
          </div>
          <div className="proj-g4__list-wrap" style={{ marginTop: '0.55rem' }}>
            <table className="proj-g4__table">
              <thead>
                <tr>
                  <th>{lab(labels, 'category')}</th>
                  <th>{lab(labels, 'original')}</th>
                  <th>{lab(labels, 'current')}</th>
                  <th>{lab(labels, 'lines')}</th>
                </tr>
              </thead>
              <tbody>
                {summary.categories.map((c) => (
                  <tr key={c.category_id}>
                    <td>{c.category_name}</td>
                    <td>{formatCurrency(c.original_budget, locale)}</td>
                    <td>{formatCurrency(c.current_budget, locale)}</td>
                    <td>{c.line_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {summary.warnings?.length ? (
            <p className="proj-g4__banner proj-g4__banner--gap">{summary.warnings.join(' Â· ')}</p>
          ) : null}
        </>
      ) : (
        !error && <div className="proj-g4__empty">{lab(labels, 'loading')}</div>
      )}
    </div>
  );
}

export function ContractorsPanel({ projects, locale, labels, selectedProjectId }: DomainCommon) {
  const project = projects.find((p) => p.id === selectedProjectId) ?? projects[0];
  const [items, setItems] = useState<ProjectCommitment[]>([]);

  useEffect(() => {
    if (!project) return;
    void (async () => {
      try {
        const res = await fetchProjectCommitments(project.id);
        setItems(res.items);
      } catch {
        setItems([]);
      }
    })();
  }, [project]);

  if (!project) return <div className="proj-g4__empty">{lab(labels, 'empty')}</div>;

  return (
    <div className="proj-g4__panel" data-testid="proj-g4-contractors">
      <h3>
        {lab(labels, 'contractorsTitle')} — {project.project_name}
      </h3>
      <p>
        <DataTag kind="live" label={lab(labels, 'liveTag')} /> {lab(labels, 'contractorsHint')}
      </p>
      <div className="proj-g4__list-wrap">
        <table className="proj-g4__table">
          <thead>
            <tr>
              <th>#</th>
              <th>{lab(labels, 'title')}</th>
              <th>{lab(labels, 'status')}</th>
              <th>{lab(labels, 'committed')}</th>
              <th>{lab(labels, 'paid')}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={5}>{lab(labels, 'empty')}</td>
              </tr>
            ) : (
              items.map((c) => (
                <tr key={c.id}>
                  <td>{c.commitment_number}</td>
                  <td>{c.title}</td>
                  <td>{c.status}</td>
                  <td>{formatCurrency(c.current_committed_amount, locale)}</td>
                  <td>{formatCurrency(c.paid_amount, locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DemoTablePanel({
  testId,
  title,
  gap,
  demoTag,
  columns,
  rows,
}: {
  testId: string;
  title: string;
  gap: string;
  demoTag: string;
  columns: string[];
  rows: string[][];
}) {
  return (
    <div className="proj-g4__panel" data-testid={testId}>
      <h3>{title}</h3>
      <p>
        <DataTag kind="demo" label={demoTag} /> {gap}
      </p>
      <div className="proj-g4__list-wrap">
        <table className="proj-g4__table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function PermitsPanel({ projects, labels }: DomainCommon) {
  const items: PermitRecord[] = listPermits(projects);
  return (
    <DemoTablePanel
      testId="proj-g4-permits"
      title={lab(labels, 'permitsTitle')}
      gap={lab(labels, 'permitsGap')}
      demoTag={lab(labels, 'demoTag')}
      columns={[lab(labels, 'project'), lab(labels, 'title'), lab(labels, 'authority'), lab(labels, 'status'), lab(labels, 'submitted')]}
      rows={items.map((p) => [p.projectName, p.name, p.authority, p.status, p.submittedAt ?? 'â€”'])}
    />
  );
}

export function InspectionsPanel({ projects, labels }: DomainCommon) {
  const items: InspectionRecord[] = listInspections(projects);
  return (
    <DemoTablePanel
      testId="proj-g4-inspections"
      title={lab(labels, 'inspectionsTitle')}
      gap={lab(labels, 'inspectionsGap')}
      demoTag={lab(labels, 'demoTag')}
      columns={[lab(labels, 'project'), lab(labels, 'title'), lab(labels, 'inspector'), lab(labels, 'status'), lab(labels, 'scheduled')]}
      rows={items.map((p) => [p.projectName, p.name, p.inspector, p.status, p.scheduledAt ?? 'â€”'])}
    />
  );
}

export function IssuesRisksPanel({ projects, labels }: DomainCommon) {
  const items: RiskRecord[] = listRisks(projects);
  return (
    <DemoTablePanel
      testId="proj-g4-issues"
      title={lab(labels, 'issuesTitle')}
      gap={lab(labels, 'issuesGap')}
      demoTag={lab(labels, 'demoTag')}
      columns={[lab(labels, 'project'), lab(labels, 'title'), lab(labels, 'severity'), lab(labels, 'status'), lab(labels, 'owner')]}
      rows={items.map((r) => [r.projectName, r.title, r.severity, r.status, r.owner])}
    />
  );
}

export function ChangeOrdersPanel({ projects, locale, labels, selectedProjectId }: DomainCommon) {
  const project = projects.find((p) => p.id === selectedProjectId) ?? projects[0];
  const local: ChangeOrderLocal[] = listLocalChangeOrders(projects);
  const [apiItems, setApiItems] = useState<ProjectCommitment[]>([]);

  useEffect(() => {
    if (!project) return;
    void (async () => {
      try {
        const res = await fetchProjectCommitments(project.id);
        setApiItems(res.items);
      } catch {
        setApiItems([]);
      }
    })();
  }, [project]);

  return (
    <div className="proj-g4__panel" data-testid="proj-g4-change-orders">
      <h3>{lab(labels, 'changeOrdersTitle')}</h3>
      <p>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} /> {lab(labels, 'changeOrdersGap')}
      </p>
      {apiItems.length > 0 ? (
        <p className="proj-g4__banner proj-g4__banner--info">
          {lab(labels, 'commitmentsWithCos')}: {apiItems.filter((c) => Number(c.approved_change_orders) > 0).length}
        </p>
      ) : null}
      <div className="proj-g4__list-wrap">
        <table className="proj-g4__table">
          <thead>
            <tr>
              <th>#</th>
              <th>{lab(labels, 'project')}</th>
              <th>{lab(labels, 'title')}</th>
              <th>{lab(labels, 'status')}</th>
              <th>{lab(labels, 'amount')}</th>
            </tr>
          </thead>
          <tbody>
            {local.map((co) => (
              <tr key={co.id}>
                <td>{co.number}</td>
                <td>{co.projectName}</td>
                <td>{co.title}</td>
                <td>{co.status}</td>
                <td>{formatCurrency(String(co.amount), locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function DocumentsPanel({ projects, labels, selectedProjectId }: DomainCommon) {
  const project = projects.find((p) => p.id === selectedProjectId) ?? projects[0];
  if (!project) return <div className="proj-g4__empty">{lab(labels, 'empty')}</div>;
  return (
    <div className="proj-g4__panel" data-testid="proj-g4-documents">
      <h3>
        {lab(labels, 'documentsTitle')} — {project.project_name}
      </h3>
      <p>
        <DataTag kind="live" label={lab(labels, 'liveTag')} /> {lab(labels, 'documentsHint')}
      </p>
      <EntityDocumentsPanel entityType="project" entityId={project.id} projectId={project.id} />
    </div>
  );
}

export function ActivityPanel({ labels }: { labels: Record<string, string> }) {
  const [items, setItems] = useState<ProjectActivityItem[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetchRecentProjectActivity({ limit: 50 });
        setItems(res.items);
      } catch {
        setItems([]);
      }
    })();
  }, []);

  const filtered = items.filter((i) => {
    if (!filter.trim()) return true;
    const q = filter.toLowerCase();
    return (
      i.title.toLowerCase().includes(q) ||
      (i.project_name ?? '').toLowerCase().includes(q) ||
      i.type.toLowerCase().includes(q)
    );
  });

  return (
    <div className="proj-g4__panel" data-testid="proj-g4-activity">
      <h3>{lab(labels, 'activityTitle')}</h3>
      <p>
        <DataTag kind="live" label={lab(labels, 'liveTag')} /> {lab(labels, 'activityHint')}
      </p>
      <input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder={lab(labels, 'filterActivity')}
        style={{
          width: '100%',
          marginBottom: '0.55rem',
          padding: '0.35rem 0.5rem',
          border: '1px solid var(--proj-border)',
          borderRadius: 6,
        }}
      />
      <div className="proj-g4__timeline">
        {filtered.map((a) => (
          <div key={a.id} className="proj-g4__timeline-item">
            <strong>{a.title}</strong>
            <span>
              {a.project_name} Â· {a.type} Â· {a.actor ?? 'â€”'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

