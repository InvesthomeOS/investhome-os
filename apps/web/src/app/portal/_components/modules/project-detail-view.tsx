'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { BarChart } from '@/components/design-system/charts/BarChart';
import { LineChart } from '@/components/design-system/charts/LineChart';

import { formatDate, formatMoney, formatPct } from '../../_lib/format';
import { getDocumentFor, getProjectFor } from '../../_lib/permissions';
import { usePortalSession } from '../../_state/portal-session';
import { PageHeader } from '../page-header';

const TABS = [
  'overview',
  'photos',
  'progress',
  'milestones',
  'budget',
  'docs',
  'news',
  'rental',
  'map',
] as const;

export function ProjectDetailView({ projectId }: { projectId: string }) {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  const [tab, setTab] = useState<(typeof TABS)[number]>('overview');

  const project = useMemo(
    () => (investorId ? getProjectFor(investorId, projectId) : null),
    [investorId, projectId],
  );

  if (!investorId) return null;

  if (!project) {
    return (
      <div className="portal-page" data-testid="portal-project-detail-missing">
        <PageHeader title={t('projects.title')} subtitle={t('projects.notFound')} classification="BLOCKED" />
        <div className="portal-empty">{t('projects.notFound')}</div>
      </div>
    );
  }

  return (
    <div className="portal-page" data-testid="portal-project-detail">
      <PageHeader title={project.name} subtitle={`${project.location} · ${project.status}`} />
      <div style={{ marginBottom: '0.5rem' }}>
        <div className="portal-list__meta" style={{ marginBottom: 4 }}>
          {t('projects.completion')} · {formatPct(project.completionPct, locale)}
        </div>
        <div className="portal-progress">
          <span style={{ width: `${project.completionPct}%` }} />
        </div>
      </div>

      <div className="portal-tabs" role="tablist" aria-label={project.name}>
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            data-testid={`portal-project-tab-${key}`}
          >
            {t(`projects.${key}`)}
          </button>
        ))}
      </div>

      {tab === 'overview' ? (
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('projects.overview')}</h2>
          <p style={{ margin: 0, lineHeight: 1.55 }}>{project.overview}</p>
        </section>
      ) : null}

      {tab === 'photos' ? (
        <section className="portal-photo-grid" data-testid="portal-project-photos">
          {project.photos.map((ph) => (
            <div key={ph.id} className={`portal-photo portal-photo--${ph.tone}`}>
              {ph.caption}
            </div>
          ))}
        </section>
      ) : null}

      {tab === 'progress' ? (
        <section className="portal-panel">
          <h2 className="portal-panel__title">{t('projects.progress')}</h2>
          <p className="portal-panel__desc">
            {formatPct(project.completionPct, locale)} complete
          </p>
          <div className="portal-progress" style={{ height: 12 }}>
            <span style={{ width: `${project.completionPct}%` }} />
          </div>
        </section>
      ) : null}

      {tab === 'milestones' ? (
        <section className="portal-panel">
          <div className="portal-list">
            {project.milestones.map((m) => (
              <div key={m.id} className="portal-list__item">
                <div>
                  <strong>{m.title}</strong>
                  <div className="portal-list__meta">{formatDate(m.date, locale)}</div>
                </div>
                <span className={`portal-status portal-status--${m.status}`}>{m.status}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {tab === 'budget' ? (
        <section className="portal-panel">
          <BarChart
            data={project.budget.map((b) => ({ label: b.label, value: b.actual }))}
            ariaLabel={t('projects.budget')}
            locale={locale}
            format="currency"
            currency="TRY"
            horizontal
          />
          <table className="portal-table" style={{ marginTop: '0.75rem' }}>
            <thead>
              <tr>
                <th />
                <th>Plan</th>
                <th>Actual</th>
              </tr>
            </thead>
            <tbody>
              {project.budget.map((b) => (
                <tr key={b.label}>
                  <td>{b.label}</td>
                  <td>{formatMoney(b.planned, locale)}</td>
                  <td>{formatMoney(b.actual, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {tab === 'docs' ? (
        <section className="portal-panel">
          <div className="portal-list">
            {project.documentIds.map((id) => {
              const doc = getDocumentFor(investorId, id);
              if (!doc) return null;
              return (
                <div key={id} className="portal-list__item">
                  <div>
                    <strong>{doc.title}</strong>
                    <div className="portal-list__meta">
                      {doc.version} · {doc.sizeLabel}
                    </div>
                  </div>
                  <a className="portal-btn" href={`/api/portal/documents/${doc.id}/download`}>
                    {t('documents.download')}
                  </a>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {tab === 'news' ? (
        <section className="portal-panel">
          {project.news.length === 0 ? (
            <div className="portal-empty">—</div>
          ) : (
            <div className="portal-list">
              {project.news.map((n) => (
                <div key={n.id} className="portal-list__item">
                  <div>
                    <strong>{n.title}</strong>
                    <div className="portal-list__meta">
                      {formatDate(n.date, locale)} · {n.summary}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {tab === 'rental' ? (
        <section className="portal-panel">
          <LineChart
            data={project.rentalProjection.map((r) => ({ label: r.month, value: r.amount }))}
            ariaLabel={t('projects.rental')}
            locale={locale}
            format="currency"
            currency="TRY"
            height={150}
          />
        </section>
      ) : null}

      {tab === 'map' ? (
        <section className="portal-map" data-testid="portal-project-map">
          <div>
            <strong>{project.map.label}</strong>
            <div>
              {project.map.lat.toFixed(4)}, {project.map.lng.toFixed(4)}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
