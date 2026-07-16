'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  fetchDesignProjects,
  formatDesignDate,
  type DesignFilters,
  type DesignProject,
} from '@/lib/api/design';
import { fetchProjects, type Project } from '@/lib/api/projects';
import { useDesignLabels } from '@/lib/i18n/design-labels';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { DesignCreateModal } from './design-create-modal';
import { DesignStudioNav } from './design-studio-nav';

const EMPTY_FILTERS: DesignFilters = {
  search: '',
  project_id: '',
  design_type: '',
  status: '',
};

export function DesignWorkspace() {
  const t = useTranslations('design');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getTypeLabel, getStatusLabel, typeOptions, statusOptions } = useDesignLabels();

  const [designs, setDesigns] = useState<DesignProject[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filters, setFilters] = useState<DesignFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<DesignFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const canCreate = user ? hasPermission(user, 'design', 'create') : false;

  const loadDesigns = useCallback(async (nextFilters: DesignFilters) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchDesignProjects(nextFilters);
      setDesigns(response.items);
    } catch {
      setError(t('loadError'));
      setDesigns([]);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadDesigns(appliedFilters);
  }, [appliedFilters, loadDesigns]);

  useEffect(() => {
    void fetchProjects().then((response) => setProjects(response.items)).catch(() => setProjects([]));
  }, []);

  const handleApplyFilters = () => setAppliedFilters({ ...filters });
  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  const handleCreated = (design: DesignProject) => {
    setShowCreate(false);
    void loadDesigns(appliedFilters);
    window.location.href = `/dashboard/design/${design.id}`;
  };

  return (
    <main className="dashboard design">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      <DesignStudioNav />

      <section className="dashboard__panel design__panel">
        <div className="leads__toolbar">
          <div className="leads__filters">
            <input
              type="search"
              className="leads__input"
              placeholder={t('filters.search')}
              value={filters.search ?? ''}
              onChange={(event) => setFilters((prev) => ({ ...prev, search: event.target.value }))}
            />
            <select
              className="leads__select"
              value={filters.project_id ?? ''}
              onChange={(event) => setFilters((prev) => ({ ...prev, project_id: event.target.value }))}
            >
              <option value="">{t('filters.allProjects')}</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.project_name}
                </option>
              ))}
            </select>
            <select
              className="leads__select"
              value={filters.design_type ?? ''}
              onChange={(event) => setFilters((prev) => ({ ...prev, design_type: event.target.value }))}
            >
              <option value="">{t('filters.allTypes')}</option>
              {typeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              className="leads__select"
              value={filters.status ?? ''}
              onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}
            >
              <option value="">{t('filters.allStatuses')}</option>
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <button type="button" className="leads__button leads__button--secondary" onClick={handleApplyFilters}>
              {tCommon('apply')}
            </button>
            <button type="button" className="leads__button leads__button--ghost" onClick={handleResetFilters}>
              {tCommon('reset')}
            </button>
          </div>
          {canCreate && (
            <button type="button" className="leads__button leads__button--primary" onClick={() => setShowCreate(true)}>
              {t('createButton')}
            </button>
          )}
        </div>

        {loading && <p className="leads__state">{tCommon('loading')}</p>}
        {error && <p className="leads__state leads__state--error">{error}</p>}
        {!loading && !error && designs.length === 0 && <p className="leads__state">{t('empty')}</p>}

        {!loading && !error && designs.length > 0 && (
          <div className="leads__table-wrap">
            <table className="leads__table">
              <thead>
                <tr>
                  <th>{t('columns.title')}</th>
                  <th>{t('columns.project')}</th>
                  <th>{t('columns.sourceDrawing')}</th>
                  <th>{t('columns.designType')}</th>
                  <th>{t('columns.status')}</th>
                  <th>{t('columns.currentVersion')}</th>
                  <th>{t('columns.updated')}</th>
                  <th>{t('columns.createdBy')}</th>
                </tr>
              </thead>
              <tbody>
                {designs.map((design) => (
                  <tr key={design.id}>
                    <td>
                      <Link href={`/dashboard/design/${design.id}` as Route} className="leads__link">
                        {design.title}
                      </Link>
                    </td>
                    <td>{design.project_name ?? tCommon('noValue')}</td>
                    <td>{design.document_title ?? tCommon('noValue')}</td>
                    <td>{getTypeLabel(design.design_type)}</td>
                    <td>{getStatusLabel(design.status)}</td>
                    <td>{design.current_version_number ?? t('noVersion')}</td>
                    <td>{formatDesignDate(design.updated_at, locale)}</td>
                    <td>{design.created_by_name ?? tCommon('noValue')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showCreate && (
        <DesignCreateModal
          projects={projects}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}
    </main>
  );
}
