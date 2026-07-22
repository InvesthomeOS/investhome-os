'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@investhome/ui';

import { canViewMarketingDashboard } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';
import { useMarketingDashboardStore } from '@/workspaces/marketing/stores/dashboard-ui-store';

import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function DashboardSettingsPage() {
  const t = useTranslations('marketing.analytics.settings');
  const editMode = useMarketingDashboardStore((s) => s.editMode);
  const toggleEditMode = useMarketingDashboardStore((s) => s.toggleEditMode);
  const resetFilters = useMarketingDashboardStore((s) => s.resetFilters);
  const { user } = useAuth();
  const canView = canViewMarketingDashboard(user);

  const savedViewsQuery = useQuery({
    ...marketingQueries.dashboardSavedViews(),
    enabled: canView,
  });

  return (
    <AnalyticsSectionPage
      titleKey="settings.title"
      subtitleKey="settings.subtitle"
      queryOptions={{ queryKey: ['marketing', 'dashboard', 'settings'], queryFn: async () => ({ ok: true }) }}
      render={() => (
        <div className="mkt-dashboard-settings">
          <section className="mkt-dashboard-settings__section">
            <h2>{t('layoutMode')}</h2>
            <Button type="button" variant={editMode ? 'primary' : 'secondary'} onClick={toggleEditMode}>
              {editMode ? t('exitEditMode') : t('enterEditMode')}
            </Button>
          </section>

          <section className="mkt-dashboard-settings__section">
            <h2>{t('filters')}</h2>
            <Button type="button" variant="secondary" onClick={resetFilters}>
              {t('resetFilters')}
            </Button>
          </section>

          <section className="mkt-dashboard-settings__section">
            <h2>{t('savedViews')}</h2>
            {(savedViewsQuery.data ?? []).length === 0 ? (
              <p className="mkt-widget__state">{t('noSavedViews')}</p>
            ) : (
              <ul className="mkt-saved-views-list">
                {savedViewsQuery.data?.map((view) => (
                  <li key={view.id}>{view.name}</li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    />
  );
}
