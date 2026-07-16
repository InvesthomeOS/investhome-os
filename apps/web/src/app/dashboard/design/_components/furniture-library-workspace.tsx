'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchFurnitureItems, type FurnitureItem } from '@/lib/api/design';
import { useDesignLabels } from '@/lib/i18n/design-labels';

import { DesignStudioNav } from './design-studio-nav';

export function FurnitureLibraryWorkspace() {
  const t = useTranslations('design.furnitureLibrary');
  const tCommon = useTranslations('common');
  const { getFurnitureTypeLabel } = useDesignLabels();
  const [items, setItems] = useState<FurnitureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchFurnitureItems();
      setItems(response.items);
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
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      <DesignStudioNav />

      <section className="dashboard__panel design__panel">
        {loading && <p className="leads__state">{tCommon('loading')}</p>}
        {error && <p className="leads__state leads__state--error">{error}</p>}
        {!loading && !error && items.length === 0 && <p className="leads__state">{t('empty')}</p>}
        {!loading && !error && items.length > 0 && (
          <div className="leads__table-wrap">
            <table className="leads__table">
              <thead>
                <tr>
                  <th>{t('columns.name')}</th>
                  <th>{t('columns.code')}</th>
                  <th>{t('columns.type')}</th>
                  <th>{t('columns.dimensions')}</th>
                  <th>{t('columns.room')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.code}</td>
                    <td>{getFurnitureTypeLabel(item.furniture_type)}</td>
                    <td>
                      {item.width && item.depth
                        ? `${item.width}×${item.depth} ${item.measurement_unit}`
                        : tCommon('noValue')}
                    </td>
                    <td>{item.room_type ?? tCommon('noValue')}</td>
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
