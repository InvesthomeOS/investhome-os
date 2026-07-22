'use client';

import { useTranslations } from 'next-intl';

import { BrandLogo } from '@/components/brand/brand-logo';
import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  AI_RECS,
  CALENDAR_DAYS,
  FINANCE_SERIES,
  INVESTORS,
  KPI_METRICS,
  MARKETING,
  PIPELINE_STAGES,
  PROJECTS,
  TASKS,
} from './demo-data';

type NavItem = { label: string; icon: IhIconName; active?: boolean };

function FinanceAreaChart() {
  const w = 640;
  const h = 240;
  const pad = { t: 16, r: 12, b: 28, l: 36 };
  const n = FINANCE_SERIES.months.length;
  const max = Math.max(...FINANCE_SERIES.collections, ...FINANCE_SERIES.disbursements) * 1.08;

  const xs = (i: number) => pad.l + (i / Math.max(n - 1, 1)) * (w - pad.l - pad.r);
  const ys = (v: number) => pad.t + ((max - v) / max) * (h - pad.t - pad.b);

  const line = (values: readonly number[]) =>
    values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xs(i).toFixed(1)} ${ys(v).toFixed(1)}`).join(' ');

  const area = (values: readonly number[]) => {
    const top = values.map((v, i) => `${xs(i).toFixed(1)},${ys(v).toFixed(1)}`).join(' ');
    return `${pad.l},${h - pad.b} ${top} ${w - pad.r},${h - pad.b}`;
  };

  return (
    <svg className="ta-spike__chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Collections vs disbursements">
      {[0.25, 0.5, 0.75, 1].map((p) => {
        const y = pad.t + (1 - p) * (h - pad.t - pad.b);
        return (
          <line
            key={p}
            x1={pad.l}
            x2={w - pad.r}
            y1={y}
            y2={y}
            stroke="#e4e7ec"
            strokeWidth={1}
          />
        );
      })}
      <polygon points={area(FINANCE_SERIES.collections)} fill="url(#taGradCollect)" opacity={0.9} />
      <polygon points={area(FINANCE_SERIES.disbursements)} fill="url(#taGradDisburse)" opacity={0.75} />
      <path d={line(FINANCE_SERIES.collections)} fill="none" stroke="#465fff" strokeWidth={2.25} />
      <path d={line(FINANCE_SERIES.disbursements)} fill="none" stroke="#9cb9ff" strokeWidth={2.25} />
      {FINANCE_SERIES.months.map((m, i) => (
        <text
          key={m}
          x={xs(i)}
          y={h - 8}
          textAnchor="middle"
          fill="#98a2b3"
          fontSize={11}
          fontFamily="Outfit, sans-serif"
        >
          {m}
        </text>
      ))}
      <defs>
        <linearGradient id="taGradCollect" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#465fff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#465fff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="taGradDisburse" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#9cb9ff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#9cb9ff" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function SalesBars() {
  const max = Math.max(...PIPELINE_STAGES.map((s) => s.count));
  return (
    <div className="ta-spike__bars" aria-hidden>
      {PIPELINE_STAGES.map((s) => (
        <div key={s.stage} className="ta-spike__bar">
          <div
            className="ta-spike__bar-fill"
            style={{ height: `${Math.max(12, (s.count / max) * 120)}px` }}
            title={`${s.stage}: ${s.count}`}
          />
          <span>{s.stage.slice(0, 3)}</span>
        </div>
      ))}
    </div>
  );
}

function MiniCal() {
  const eventByDay = new Map<number, (typeof CALENDAR_DAYS)[number]>(
    CALENDAR_DAYS.map((e) => [e.day, e]),
  );
  // July 2026 starts on Wednesday — pad 3 muted cells
  const cells: Array<{ day: number | null; event?: (typeof CALENDAR_DAYS)[number] }> = [];
  for (let i = 0; i < 3; i += 1) cells.push({ day: null });
  for (let d = 1; d <= 31; d += 1) {
    cells.push({ day: d, event: eventByDay.get(d) });
  }
  return (
    <div className="ta-spike__cal" aria-label="July 2026 calendar">
      {cells.map((c, i) => {
        if (c.day == null) {
          return <div key={`pad-${i}`} className="ta-spike__cal-cell ta-spike__cal-cell--muted" />;
        }
        if (c.event) {
          return (
            <div
              key={c.day}
              className={`ta-spike__cal-cell ta-spike__cal-cell--event ta-spike__cal-cell--${c.event.tone}`}
              title={c.event.label}
            >
              {c.day}
              <small>{c.event.label}</small>
            </div>
          );
        }
        return (
          <div key={c.day} className="ta-spike__cal-cell">
            {c.day}
          </div>
        );
      })}
    </div>
  );
}

export function TailAdminSpikePreview() {
  const t = useTranslations('navigation');

  const commandItems: NavItem[] = [{ label: t('mainMenu'), icon: 'home' }];
  const workspaceItems: NavItem[] = [
    { label: t('modules.executive.title'), icon: 'executive', active: true },
    { label: t('modules.sales.title'), icon: 'sales' },
    { label: t('modules.investors.title'), icon: 'investors' },
    { label: t('modules.projects.title'), icon: 'projects' },
    { label: t('modules.inventory.title'), icon: 'inventory' },
    { label: t('modules.finance.title'), icon: 'finance' },
    { label: t('modules.crm.title'), icon: 'crm' },
    { label: t('modules.marketing.title'), icon: 'marketing' },
    { label: t('modules.company.title'), icon: 'executive' },
  ];
  const toolItems: NavItem[] = [
    { label: t('businessIntelligence'), icon: 'barChart' },
    { label: t('aiWorkspace'), icon: 'sparkles' },
    { label: t('knowledgeHub'), icon: 'documents' },
    { label: t('designStudio'), icon: 'design' },
    { label: t('activity'), icon: 'activity' },
    { label: t('automation'), icon: 'refresh' },
    { label: t('settings'), icon: 'settings' },
  ];
  const adminItems: NavItem[] = [
    { label: t('adminSection'), icon: 'admin' },
    { label: t('admin.users'), icon: 'users' },
    { label: t('admin.roles'), icon: 'roles' },
    { label: t('admin.permissions'), icon: 'permissions' },
  ];

  const renderNav = (items: NavItem[]) =>
    items.map((item) => (
      <div
        key={item.label}
        className={`ta-spike__nav-link${item.active ? ' ta-spike__nav-link--active' : ''}`}
        aria-current={item.active ? 'page' : undefined}
      >
        <span className="ta-spike__nav-ico">
          <IhIcon name={item.icon} size="nav" />
        </span>
        <span>{item.label}</span>
      </div>
    ));

  return (
    <div className="ta-spike" data-testid="tailadmin-spike-preview">
      <aside className="ta-spike__sidebar" aria-label={t('ariaLabel')}>
        <div className="ta-spike__brand">
          <BrandLogo layout="full" tone="color" />
          <div className="ta-spike__brand-meta">
            <strong>Investhome OS</strong>
            <span>TailAdmin spike · demo</span>
          </div>
        </div>

        <div className="ta-spike__nav-section">{t('commandSection')}</div>
        {renderNav(commandItems)}

        <div className="ta-spike__nav-section">{t('workspacesSection')}</div>
        {renderNav(workspaceItems)}

        <div className="ta-spike__nav-section">{t('toolsSection')}</div>
        {renderNav(toolItems)}

        <div className="ta-spike__nav-section">{t('adminSection')}</div>
        {renderNav(adminItems)}

        <div className="ta-spike__sidebar-foot">
          <strong>Free edition only</strong>
          Isolated visual POC — no production API mutations. Removable via `_tailadmin/`.
        </div>
      </aside>

      <div className="ta-spike__main">
        <header className="ta-spike__header">
          <div>
            <h1>Executive overview</h1>
            <p>Dense TailAdmin-style layout · demo data · July 2026</p>
          </div>
          <span className="ta-spike__badge">Admin preview · not live</span>
        </header>

        <div className="ta-spike__content">
          <section className="ta-spike__kpi-grid" aria-label="KPI cards">
            {KPI_METRICS.map((kpi) => (
              <article key={kpi.id} className="ta-spike__kpi">
                <div className="ta-spike__kpi-icon" aria-hidden>
                  <IhIcon
                    name={
                      kpi.id === 'revenue'
                        ? 'finance'
                        : kpi.id === 'pipeline'
                          ? 'sales'
                          : kpi.id === 'equity'
                            ? 'investors'
                            : 'projects'
                    }
                    size="nav"
                  />
                </div>
                <div className="ta-spike__kpi-row">
                  <div>
                    <span className="ta-spike__kpi-label">{kpi.label}</span>
                    <span className="ta-spike__kpi-value">{kpi.value}</span>
                  </div>
                  <span className={`ta-spike__delta ta-spike__delta--${kpi.up ? 'up' : 'down'}`}>
                    {kpi.delta}
                  </span>
                </div>
              </article>
            ))}
          </section>

          <section className="ta-spike__grid-2">
            <article className="ta-spike__card">
              <div className="ta-spike__card-head">
                <div>
                  <h2>Financial performance</h2>
                  <p>Collections vs disbursements (₺M) — demo series</p>
                </div>
                <div className="ta-spike__chart-legend">
                  <span>
                    <i className="ta-spike__legend-dot" style={{ background: '#465fff' }} />
                    Collections
                  </span>
                  <span>
                    <i className="ta-spike__legend-dot" style={{ background: '#9cb9ff' }} />
                    Disbursements
                  </span>
                </div>
              </div>
              <FinanceAreaChart />
            </article>

            <article className="ta-spike__card">
              <div className="ta-spike__card-head">
                <div>
                  <h2>Sales pipeline</h2>
                  <p>Stage volume and weighted value</p>
                </div>
              </div>
              <div className="ta-spike__pipeline">
                {PIPELINE_STAGES.map((s) => (
                  <div key={s.stage} className="ta-spike__pipe-stage">
                    <span>{s.stage}</span>
                    <strong>{s.count}</strong>
                    <em>{s.value}</em>
                  </div>
                ))}
              </div>
              <SalesBars />
            </article>
          </section>

          <section className="ta-spike__grid-3">
            <article className="ta-spike__card">
              <div className="ta-spike__card-head">
                <div>
                  <h2>Projects</h2>
                  <p>Delivery health and budget envelope</p>
                </div>
              </div>
              <table className="ta-spike__table">
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Progress</th>
                    <th>Health</th>
                  </tr>
                </thead>
                <tbody>
                  {PROJECTS.map((p) => (
                    <tr key={p.name}>
                      <td>
                        <strong>{p.name}</strong>
                        <div className="ta-spike__task-meta">
                          {p.phase} · {p.budget}
                        </div>
                      </td>
                      <td>
                        <div className="ta-spike__progress" title={`${p.progress}%`}>
                          <span style={{ width: `${p.progress}%` }} />
                        </div>
                      </td>
                      <td>
                        <span
                          className={`ta-spike__pill ta-spike__pill--${
                            p.health === 'on_track' ? 'ok' : p.health === 'watch' ? 'watch' : 'risk'
                          }`}
                        >
                          {p.health === 'on_track' ? 'On track' : p.health === 'watch' ? 'Watch' : 'Risk'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>

            <article className="ta-spike__card">
              <div className="ta-spike__card-head">
                <div>
                  <h2>Investors</h2>
                  <p>Commitments and next actions</p>
                </div>
              </div>
              <table className="ta-spike__table">
                <thead>
                  <tr>
                    <th>Partner</th>
                    <th>Commitment</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {INVESTORS.map((inv) => (
                    <tr key={inv.name}>
                      <td>
                        <strong>{inv.name}</strong>
                        <div className="ta-spike__task-meta">{inv.next}</div>
                      </td>
                      <td>{inv.commitment}</td>
                      <td>
                        <span
                          className={`ta-spike__pill ta-spike__pill--${
                            inv.status === 'Active'
                              ? 'ok'
                              : inv.status === 'Watch'
                                ? 'watch'
                                : 'watch'
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>

            <article className="ta-spike__card">
              <div className="ta-spike__card-head">
                <div>
                  <h2>Tasks</h2>
                  <p>Executive action queue</p>
                </div>
              </div>
              {TASKS.map((task) => (
                <div key={task.title} className="ta-spike__task">
                  <div>
                    <strong>{task.title}</strong>
                    <div className="ta-spike__task-meta">
                      {task.owner} · due {task.due}
                    </div>
                  </div>
                  <span className={`ta-spike__pri ta-spike__pri--${task.priority}`}>{task.priority}</span>
                </div>
              ))}
            </article>
          </section>

          <section className="ta-spike__grid-2eq">
            <article className="ta-spike__card">
              <div className="ta-spike__card-head">
                <div>
                  <h2>Calendar</h2>
                  <p>July 2026 — key operating dates</p>
                </div>
              </div>
              <MiniCal />
            </article>

            <article className="ta-spike__card">
              <div className="ta-spike__card-head">
                <div>
                  <h2>Marketing</h2>
                  <p>Campaign spend and lead efficiency</p>
                </div>
              </div>
              <table className="ta-spike__table">
                <thead>
                  <tr>
                    <th>Campaign</th>
                    <th>Spend</th>
                    <th>Leads</th>
                    <th>CPL</th>
                  </tr>
                </thead>
                <tbody>
                  {MARKETING.map((m) => (
                    <tr key={m.campaign}>
                      <td>
                        <strong>{m.campaign}</strong>
                        <div className="ta-spike__task-meta">{m.channel}</div>
                      </td>
                      <td>{m.spend}</td>
                      <td>{m.leads}</td>
                      <td>{m.cpl}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          </section>

          <section className="ta-spike__card">
            <div className="ta-spike__card-head">
              <div>
                <h2>AI recommendations</h2>
                <p>Advisory only — demo narratives, no auto-execution</p>
              </div>
            </div>
            <div className="ta-spike__ai">
              {AI_RECS.map((rec) => (
                <div key={rec.title} className="ta-spike__ai-item">
                  <strong>{rec.title}</strong>
                  <p>{rec.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <p className="ta-spike__note">
            Compatibility spike · TailAdmin Free visual language · INVESTHOME OS labels & logo · removable
            `_tailadmin/` tree
          </p>
        </div>
      </div>
    </div>
  );
}
