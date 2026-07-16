'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchStylePresets, type StylePreset } from '@/lib/api/design';

import { DesignStudioNav } from './design-studio-nav';

export function StylePresetsWorkspace() {
  const t = useTranslations('design.stylePresets');
  const tCommon = useTranslations('common');
  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchStylePresets();
      setPresets(response.items);
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
        {!loading && !error && presets.length === 0 && <p className="leads__state">{t('empty')}</p>}
        {!loading && !error && presets.length > 0 && (
          <div className="leads__table-wrap">
            <table className="leads__table">
              <thead>
                <tr>
                  <th>{t('columns.name')}</th>
                  <th>{t('columns.code')}</th>
                  <th>{t('columns.type')}</th>
                  <th>{t('columns.description')}</th>
                </tr>
              </thead>
              <tbody>
                {presets.map((preset) => (
                  <tr key={preset.id}>
                    <td>{preset.name}</td>
                    <td>{preset.code}</td>
                    <td>{preset.is_system_preset ? t('system') : t('custom')}</td>
                    <td>{preset.description ?? tCommon('noValue')}</td>
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
