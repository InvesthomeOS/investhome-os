'use client';

import type { Route } from 'next';
import Link from 'next/link';

import { MosaicAvatar } from './MosaicAvatar';
import { RevenueSalesChart } from './RevenueChart';
import {
  ACTIVITY_FEED,
  INVESTOR_FOLLOWUPS,
  MOSAIC_KPIS,
  PIPELINE_STAGES,
  PROJECT_STATUS,
  RECENT_LEADS,
  TASKS,
} from './demo-data';
import { healthClass, healthLabel, statusClass } from './status';

export function DashboardView() {
  const maxCount = Math.max(...PIPELINE_STAGES.map((s) => s.count));

  return (
    <div className="mosaic-dash" data-testid="mosaic-dashboard">
      <section className="mosaic-kpi-row">
        {MOSAIC_KPIS.map((kpi) => (
          <article key={kpi.id} className="mosaic-card mosaic-kpi">
            <p className="mosaic-kpi__label">{kpi.label}</p>
            <p className="mosaic-kpi__value">{kpi.value}</p>
            <p className={`mosaic-kpi__delta${kpi.up ? ' is-up' : ' is-down'}`}>{kpi.delta}</p>
          </article>
        ))}
      </section>

      <section className="mosaic-grid mosaic-grid--2">
        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Sales pipeline</h2>
            <span className="mosaic-muted">₺42.8M open</span>
          </header>
          <div className="mosaic-pipeline">
            {PIPELINE_STAGES.map((s) => (
              <div key={s.stage} className="mosaic-pipeline__row">
                <div className="mosaic-pipeline__meta">
                  <strong>{s.stage}</strong>
                  <span>
                    {s.count} · {s.value}
                  </span>
                </div>
                <div className="mosaic-pipeline__track">
                  <div
                    className="mosaic-pipeline__fill"
                    style={{
                      width: `${Math.max(8, (s.count / maxCount) * 100)}%`,
                      background: s.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Investor follow-up</h2>
            <span className="mosaic-muted">This week</span>
          </header>
          <ul className="mosaic-list">
            {INVESTOR_FOLLOWUPS.map((inv) => (
              <li key={inv.id} className="mosaic-list__item">
                <MosaicAvatar name={inv.contact} size="md" tone={inv.tone} />
                <div className="mosaic-list__body">
                  <strong>{inv.name}</strong>
                  <span>
                    {inv.contact} · {inv.next}
                  </span>
                </div>
                <div className="mosaic-list__aside">
                  <span className={`mosaic-badge ${statusClass(inv.status)}`}>{inv.status}</span>
                  <small>{inv.due}</small>
                </div>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="mosaic-grid mosaic-grid--2">
        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Project status</h2>
          </header>
          <ul className="mosaic-projects">
            {PROJECT_STATUS.map((p) => (
              <li key={p.name}>
                <div className="mosaic-projects__top">
                  <div>
                    <strong>{p.name}</strong>
                    <span>
                      {p.phase} · {p.budget}
                    </span>
                  </div>
                  <span className={`mosaic-health ${healthClass(p.health)}`}>{healthLabel(p.health)}</span>
                </div>
                <div className="mosaic-progress">
                  <div className="mosaic-progress__fill" style={{ width: `${p.progress}%` }} />
                </div>
                <small>{p.progress}%</small>
              </li>
            ))}
          </ul>
        </article>

        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Revenue / sales</h2>
            <span className="mosaic-muted">YTD ₺M</span>
          </header>
          <RevenueSalesChart />
        </article>
      </section>

      <section className="mosaic-grid mosaic-grid--3">
        <article className="mosaic-card mosaic-card--span2">
          <header className="mosaic-card__head">
            <h2>Recent leads</h2>
            <Link href={'/ui-preview/mosaic/leads' as Route} className="mosaic-link">
              View all
            </Link>
          </header>
          <div className="mosaic-table-wrap">
            <table className="mosaic-table">
              <thead>
                <tr>
                  <th>Lead</th>
                  <th>Project</th>
                  <th>Owner</th>
                  <th>Status</th>
                  <th>Next</th>
                </tr>
              </thead>
              <tbody>
                {RECENT_LEADS.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <div className="mosaic-person">
                        <MosaicAvatar name={lead.name} size="sm" />
                        <div>
                          <Link href={'/ui-preview/mosaic/customer' as Route} className="mosaic-link-strong">
                            {lead.name}
                          </Link>
                          <span>{lead.source}</span>
                        </div>
                      </div>
                    </td>
                    <td>{lead.project}</td>
                    <td>{lead.salesperson}</td>
                    <td>
                      <span className={`mosaic-badge ${statusClass(lead.status)}`}>{lead.status}</span>
                    </td>
                    <td className="mosaic-muted">{lead.nextAction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="mosaic-card">
          <header className="mosaic-card__head">
            <h2>Activity</h2>
          </header>
          <ul className="mosaic-activity">
            {ACTIVITY_FEED.map((a) => (
              <li key={a.id}>
                <MosaicAvatar name={a.actor} size="sm" tone={a.tone} />
                <div>
                  <p>
                    <strong>{a.actor}</strong> {a.action}
                  </p>
                  <small>{a.time}</small>
                </div>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="mosaic-card">
        <header className="mosaic-card__head">
          <h2>Tasks</h2>
          <span className="mosaic-muted">{TASKS.filter((t) => !t.done).length} open</span>
        </header>
        <ul className="mosaic-tasks">
          {TASKS.map((t) => (
            <li key={t.id} className={t.done ? 'is-done' : ''}>
              <span className={`mosaic-check${t.done ? ' is-on' : ''}`} aria-hidden>
                {t.done ? '✓' : ''}
              </span>
              <div>
                <strong>{t.title}</strong>
                <span>
                  {t.owner} · {t.due}
                </span>
              </div>
              <span className={`mosaic-prio mosaic-prio--${t.priority}`}>{t.priority}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
