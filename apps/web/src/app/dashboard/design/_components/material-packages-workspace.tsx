'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { DashboardHeaderActions } from '@/app/dashboard/_components/dashboard-header-actions';
import { fetchMaterialPackages, type MaterialPackage } from '@/lib/api/design';

import { DesignStudioNav } from './design-studio-nav';

export function MaterialPackagesWorkspace() {
  const t = useTranslations('design.materialPackages');
  const tCommon = useTranslations('common');
  const [packages, setPackages] = useState<MaterialPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchMaterialPackages();
      setPackages(response.items);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="dashboard design">
      <header className="dashboard__header">
        <div>
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        <DashboardHeaderActions />
      </header>

      <DesignStudioNav />

      <section className="dashboard__panel design__panel">
        {loading && <p className="leads__state">{tCommon('loading')}</p>}
        {error && <p className="leads__state leads__state--error">{error}</p>}
        {!loading && !error && packages.length === 0 && <p className="leads__state">{t('empty')}</p>}
        {!loading && !error && packages.length > 0 && (
          <div className="leads__table-wrap">
            <table className="leads__table">
              <thead>
                <tr>
                  <th>{t('columns.name')}</th>
                  <th>{t('columns.flooring')}</th>
                  <th>{t('columns.walls')}</th>
                  <th>{t('columns.description')}</th>
                </tr>
              </thead>
              <tbody>
                {packages.map((pkg) => (
                  <tr key={pkg.id}>
                    <td>{pkg.name}</td>
                    <td>{pkg.flooring ?? tCommon('noValue')}</td>
                    <td>{pkg.wall_finish ?? tCommon('noValue')}</td>
                    <td>{pkg.description ?? tCommon('noValue')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
