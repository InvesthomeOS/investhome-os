'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, type ReactNode } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { hasPermission } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';
import {
  visibleSettingsEntries,
  type SettingsGroupId,
} from '@/lib/settings/settings-catalog';
import { fetchCommunicationAccounts, fetchGmailStatus } from '@/workspaces/crm/api/communication';

const COPY = {
  tr: {
    title: 'CRM Ayarları',
    subtitle: 'Yalnızca CRM davranışını etkileyen yapılandırma.',
    manage: 'Yönet',
    pipeline: 'Pipeline aşamaları',
    opportunity: 'Fırsat aşamaları',
    activityTypes: 'Aktivite türleri',
    taskTypes: 'Görev türleri',
    tags: 'Etiketler',
    commAccounts: 'İletişim hesapları',
    connected: 'Bağlı',
    notConnected: 'Bağlı değil',
    none: '—',
    pipelineValue: 'Pipeline ekranından yönetilir',
    opportunityValue: 'Anlaşmalar ekranında görüntülenir',
    activityValue: 'İletişim ekranından yönetilir',
    taskValue: 'Görevler ekranından yönetilir',
    accessDenied: 'CRM ayarlarını görüntüleme yetkiniz yok.',
    related: 'İlgili ayarlar',
  },
  en: {
    title: 'CRM settings',
    subtitle: 'Configuration that affects CRM behavior only.',
    manage: 'Manage',
    pipeline: 'Pipeline stages',
    opportunity: 'Opportunity stages',
    activityTypes: 'Activity types',
    taskTypes: 'Task types',
    tags: 'Tags',
    commAccounts: 'Communication accounts',
    connected: 'Connected',
    notConnected: 'Not connected',
    none: '—',
    pipelineValue: 'Managed on the Pipeline screen',
    opportunityValue: 'Viewed on the Agreements screen',
    activityValue: 'Managed on the Communication screen',
    taskValue: 'Managed on the Tasks screen',
    accessDenied: 'You do not have permission to view CRM settings.',
    related: 'Related settings',
  },
};

function ActionLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href as Route} className="ih-btn ih-btn--secondary ih-btn--sm">
      {children}
    </Link>
  );
}

export function CrmSettingsLiveWorkspace() {
  const locale = useLocale();
  const copy = locale.startsWith('en') ? COPY.en : COPY.tr;
  const tSettings = useTranslations('settings');
  const { authLoading, user, canRead } = useCrmAccess();
  const canView = Boolean(user && (canRead || hasPermission(user, 'settings', 'view')));
  const related = useMemo(
    () => visibleSettingsEntries(user).filter((entry) => entry.id !== 'crmSettings' && entry.id !== 'communicationAccounts'),
    [user],
  );

  const tagsQuery = useQuery({
    ...crmQueries.tags(),
    enabled: !authLoading && canView,
    retry: false,
  });
  const accountsQuery = useQuery({
    queryKey: ['crm', 'communications', 'accounts'],
    queryFn: () => fetchCommunicationAccounts(),
    enabled: !authLoading && canView,
    retry: false,
  });
  const gmailQuery = useQuery({
    queryKey: ['crm', 'communications', 'gmail-status'],
    queryFn: fetchGmailStatus,
    enabled: !authLoading && canView,
    retry: false,
  });

  const accounts = accountsQuery.data?.items ?? [];
  const emailConnected = accounts.some((item) => item.channel_type === 'email' && item.status === 'connected');
  const whatsappConnected = accounts.some(
    (item) => item.channel_type === 'whatsapp' && item.status === 'connected',
  );
  const gmailConnected =
    (gmailQuery.data?.connected_count ?? 0) > 0 ||
    accounts.some((item) => item.provider === 'gmail' && item.status === 'connected');

  const rows = useMemo(
    () => [
      { id: 'pipeline', icon: 'barChart' as const, title: copy.pipeline, value: copy.pipelineValue, href: '/workspaces/crm/pipeline' },
      { id: 'opportunity', icon: 'target' as const, title: copy.opportunity, value: copy.opportunityValue, href: '/workspaces/crm/agreements' },
      { id: 'activity', icon: 'activity' as const, title: copy.activityTypes, value: copy.activityValue, href: '/workspaces/crm/communication' },
      { id: 'tasks', icon: 'check' as const, title: copy.taskTypes, value: copy.taskValue, href: '/workspaces/crm/tasks' },
      {
        id: 'tags',
        icon: 'inventory' as const,
        title: copy.tags,
        value:
          tagsQuery.data?.stats?.total_tags != null
            ? String(tagsQuery.data.stats.total_tags)
            : tagsQuery.data?.items
              ? String(tagsQuery.data.items.length)
              : copy.none,
        href: '/workspaces/crm/tags',
      },
      {
        id: 'accounts',
        icon: 'mail' as const,
        title: copy.commAccounts,
        value: emailConnected || whatsappConnected || gmailConnected ? copy.connected : copy.notConnected,
        href: '/workspaces/crm/settings/communication-accounts',
      },
    ],
    [copy, emailConnected, gmailConnected, tagsQuery.data, whatsappConnected],
  );

  if (authLoading || (canView && tagsQuery.isLoading && !tagsQuery.data)) {
    return <LoadingState />;
  }
  if (!canView) {
    return <ErrorState title={copy.title} message={copy.accessDenied} />;
  }

  const crossGroups: SettingsGroupId[] = ['personal', 'platform', 'integrations', 'access', 'security'];

  return (
    <div className="crm-ops crm-ops--settings" data-testid="crm-settings-workspace">
      <header className="crm-ops__header">
        <div className="crm-ops__title">
          <span className="crm-ops__title-icon" aria-hidden>
            <IhIcon name="settings" size={18} />
          </span>
          <div>
            <h1>{copy.title}</h1>
            <p>{copy.subtitle}</p>
          </div>
        </div>
        <div className="crm-ops__header-tools">
          <ActionLink href="/workspaces/crm/settings/communication-accounts">{copy.commAccounts}</ActionLink>
        </div>
      </header>

      <article className="crm-ops-card">
        <header className="crm-ops-card__head">
          <h2 className="crm-ops-card__title">
            <span aria-hidden>
              <IhIcon name="crm" size={14} />
            </span>
            {copy.title}
          </h2>
        </header>
        <ul className="crm-ops-rows">
          {rows.map((row) => (
            <li key={row.id} className="crm-ops-row">
              <span className="crm-ops-row__icon" aria-hidden>
                <IhIcon name={row.icon as IhIconName} size={13} />
              </span>
              <span className="crm-ops-row__copy">
                <strong>{row.title}</strong>
              </span>
              <em className="crm-ops-row__meta">{row.value}</em>
              <ActionLink href={row.href}>{copy.manage}</ActionLink>
            </li>
          ))}
        </ul>
      </article>

      <section className="settings-related" aria-label={copy.related} data-testid="crm-settings-related">
        <h2 className="settings-nav-group__label">{copy.related}</h2>
        {crossGroups.map((group) => {
          const links = related.filter((entry) => entry.group === group);
          if (!links.length) return null;
          return (
            <div key={group}>
              <p className="settings-nav-group__label">{tSettings(`groups.${group}`)}</p>
              <div className="settings-related__links">
                {links.map((entry) => (
                  <Link key={entry.id} href={entry.href as Route}>
                    {entry.tab
                      ? tSettings(`tabs.${entry.tab}` as 'tabs.company')
                      : tSettings(`catalog.${entry.id}` as 'catalog.profile')}
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}
