'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';

import { formatPct } from '../../_lib/format';
import { getProjectsFor } from '../../_lib/permissions';
import { usePortalSession } from '../../_state/portal-session';
import { PageHeader } from '../page-header';

export function ProjectsView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  if (!investorId) return null;
  const projects = getProjectsFor(investorId);

  return (
    <div className="portal-page" data-testid="portal-projects">
      <PageHeader title={t('projects.title')} subtitle={t('projects.subtitle')} />
      <div className="portal-grid-3">
        {projects.map((p) => (
          <article key={p.id} className="portal-panel" data-testid={`portal-project-card-${p.id}`}>
            <h2 className="portal-panel__title">{p.name}</h2>
            <p className="portal-panel__desc">{p.location}</p>
            <div style={{ marginBottom: '0.65rem' }}>
              <div className="portal-list__meta" style={{ marginBottom: 4 }}>
                {t('projects.completion')} · {formatPct(p.completionPct, locale)}
              </div>
              <div className="portal-progress">
                <span style={{ width: `${p.completionPct}%` }} />
              </div>
            </div>
            <span className={`portal-status portal-status--${p.status}`}>{p.status}</span>
            <div style={{ marginTop: '0.85rem' }}>
              <Link className="portal-btn portal-btn--primary" href={`/portal/projects/${p.id}` as Route}>
                {t('projects.open')}
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
