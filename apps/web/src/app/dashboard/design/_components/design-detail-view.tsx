'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import {
  archiveDesignProject,
  fetchDesignProject,
  fetchDesignVersions,
  formatDesignDate,
  type DesignProject,
  type DesignVersion,
} from '@/lib/api/design';
import { drawingPreviewUrl } from '@/lib/api/drawing-intelligence';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useDesignLabels } from '@/lib/i18n/design-labels';

import { ColorStudio } from './color-studio';

type DetailTab =
  | 'overview'
  | 'source'
  | 'colorStudio'
  | 'versions'
  | 'related'
  | 'activity';

interface DesignDetailViewProps {
  designId: string;
}

export function DesignDetailView({ designId }: DesignDetailViewProps) {
  const t = useTranslations('design.detail');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getTypeLabel, getStatusLabel } = useDesignLabels();

  const [design, setDesign] = useState<DesignProject | null>(null);
  const [versions, setVersions] = useState<DesignVersion[]>([]);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const canArchive = user ? hasPermission(user, 'design', 'archive') : false;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [project, versionList] = await Promise.all([
        fetchDesignProject(designId),
        fetchDesignVersions(designId),
      ]);
      setDesign(project);
      setVersions(versionList.items);
    } catch {
      setError(t('loadError'));
      setDesign(null);
      setVersions([]);
    } finally {
      setLoading(false);
    }
  }, [designId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const latestVersion = useMemo(
    () => versions.reduce<DesignVersion | null>((best, item) => {
      if (!best || item.version_number > best.version_number) return item;
      return best;
    }, null),
    [versions],
  );

  const runAction = async (action: () => Promise<DesignProject>) => {
    if (!design) return;
    setActionError(null);
    try {
      const updated = await action();
      setDesign(updated);
      void load();
    } catch {
      setActionError(t('actionError'));
    }
  };

  if (loading) {
    return <main className="dashboard design"><p className="leads__state">{tCommon('loading')}</p></main>;
  }

  if (error || !design) {
    return (
      <main className="dashboard design">
        <p className="leads__state leads__state--error">{error ?? t('loadError')}</p>
        <Link href={'/dashboard/design' as Route} className="leads__button leads__button--secondary">
          {t('backToList')}
        </Link>
      </main>
    );
  }

  const tabs: { id: DetailTab; label: string }[] = [
    { id: 'overview', label: t('tabs.overview') },
    { id: 'source', label: t('tabs.sourcePlan') },
    { id: 'colorStudio', label: t('tabs.colorStudio') },
    { id: 'versions', label: t('tabs.versions') },
    { id: 'related', label: t('tabs.relatedRecords') },
    { id: 'activity', label: t('tabs.activity') },
  ];

  return (
    <main className="dashboard design design-detail">
      <header className="dashboard__header">
        <div>
          <Link href={'/dashboard/design' as Route} className="dashboard__eyebrow">
            {t('backToList')}
          </Link>
          <h1 className="dashboard__title">{design.title}</h1>
          <p className="dashboard__subtitle">
            {design.project_name} · {getTypeLabel(design.design_type)} · {getStatusLabel(design.status)}
          </p>
        </div>
        <div className="design-detail__actions">
          {canArchive && !design.archived_at && (
            <button type="button" className="leads__button leads__button--ghost" onClick={() => void runAction(() => archiveDesignProject(design.id))}>
              {t('archive')}
            </button>
          )}
        </div>
      </header>

      {actionError && <p className="leads__state leads__state--error">{actionError}</p>}

      <nav className="documents-tabs" aria-label={t('tabsLabel')}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`documents-tabs__tab${activeTab === tab.id ? ' documents-tabs__tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <section className="dashboard__panel design-detail__panel">
        {activeTab === 'overview' && (
          <dl className="leads-detail__grid">
            <div><dt>{t('fields.project')}</dt><dd>{design.project_name ?? tCommon('noValue')}</dd></div>
            <div><dt>{t('fields.sourceDrawing')}</dt><dd>{design.document_title ?? tCommon('noValue')}</dd></div>
            <div><dt>{t('fields.designType')}</dt><dd>{getTypeLabel(design.design_type)}</dd></div>
            <div><dt>{t('fields.status')}</dt><dd>{getStatusLabel(design.status)}</dd></div>
            <div><dt>{t('fields.currentVersion')}</dt><dd>{design.current_version_number ?? t('noVersion')}</dd></div>
            <div><dt>{t('fields.createdBy')}</dt><dd>{design.created_by_name ?? tCommon('noValue')}</dd></div>
            <div><dt>{t('fields.updated')}</dt><dd>{formatDesignDate(design.updated_at, locale)}</dd></div>
            <div className="leads-detail__grid--full">
              <dt>{t('fields.description')}</dt>
              <dd>{design.description ?? tCommon('noValue')}</dd>
            </div>
          </dl>
        )}

        {activeTab === 'source' && (
          <div className="documents-preview">
            <iframe
              title={design.document_title ?? design.title}
              src={drawingPreviewUrl(design.document_id)}
              className="documents-preview__frame"
            />
          </div>
        )}

        {activeTab === 'colorStudio' && (
          <ColorStudio design={design} latestVersion={latestVersion} onVersionSaved={() => void load()} />
        )}

        {activeTab === 'versions' && (
          <div className="design-versions">
            {versions.length === 0 && <p className="leads__state">{t('noVersions')}</p>}
            {versions.map((version) => (
              <article key={version.id} className="design-versions__item">
                <h3>{t('versionLabel', { number: version.version_number })}</h3>
                <dl className="leads-detail__grid">
                  <div>
                    <dt>{t('versionSavedAt')}</dt>
                    <dd>{formatDesignDate(version.created_at, locale)}</dd>
                  </div>
                  <div>
                    <dt>{t('versionSavedBy')}</dt>
                    <dd>{version.created_by_name ?? tCommon('noValue')}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}

        {activeTab === 'related' && (
          <dl className="leads-detail__grid">
            <div>
              <dt>{t('fields.project')}</dt>
              <dd>
                <Link href={`/dashboard/projects?id=${design.project_id}` as Route}>
                  {design.project_name ?? design.project_id}
                </Link>
              </dd>
            </div>
            <div>
              <dt>{t('fields.sourceDrawing')}</dt>
              <dd>
                <Link href={`/dashboard/documents?id=${design.document_id}` as Route}>
                  {design.document_title ?? design.document_id}
                </Link>
              </dd>
            </div>
          </dl>
        )}

        {activeTab === 'activity' && (
          <EntityActivityTimeline entityType="design_project" entityId={design.id} />
        )}
      </section>
    </main>
  );
}
