'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState, type ReactNode } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchRoles, fetchUsers, hasPermission } from '@/lib/api/auth';
import {
  fetchBrands,
  fetchCompanyProfile,
  fetchPreferences,
  fetchProviderStatuses,
  type PreferenceItem,
  type ProviderStatus,
} from '@/lib/api/company-foundation';
import { fetchApiKeys, fetchMfaPolicy, fetchSystemHealth } from '@/lib/api/security-center';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';
import { fetchCommunicationAccounts, fetchGmailStatus } from '@/workspaces/crm/api/communication';

type TabId =
  | 'general'
  | 'crm'
  | 'ai'
  | 'users'
  | 'notifications'
  | 'integrations'
  | 'security'
  | 'system'
  | 'billing';

type BadgeTone = 'ok' | 'muted' | 'warn' | 'danger';

const TABS: TabId[] = [
  'general',
  'crm',
  'ai',
  'users',
  'notifications',
  'integrations',
  'security',
  'system',
  'billing',
];

const COPY = {
  tr: {
    title: 'Ayarlar',
    subtitle: 'Sistem yapılandırmasını ve bağlantıları yönetin.',
    commAccounts: 'İletişim Hesapları',
    history: 'Değişiklik Geçmişi',
    editSettings: 'Ayarları Düzenle',
    edit: 'Düzenle',
    manage: 'Yönet',
    connect: 'Bağla',
    details: 'Detayları Gör',
    general: 'Genel Ayarlar',
    crm: 'CRM Yapılandırması',
    notifications: 'Bildirim Kanalları',
    ai: 'AI Yapılandırması',
    integrations: 'Entegrasyonlar',
    security: 'Güvenlik',
    users: 'Kullanıcılar & Roller',
    billing: 'Faturalama',
    company: 'Şirket',
    language: 'Dil',
    timezone: 'Saat Dilimi',
    companyId: 'Şirket Kimliği',
    logo: 'Logo',
    lastUpdated: 'Son Güncelleme',
    pipeline: 'Pipeline Aşamaları',
    opportunity: 'Fırsat Aşamaları',
    activityTypes: 'Aktivite Türleri',
    taskTypes: 'Görev Türleri',
    tags: 'Etiketler',
    email: 'E-posta',
    whatsapp: 'WhatsApp',
    sms: 'SMS',
    gmail: 'Gmail',
    provider: 'Provider',
    model: 'Model',
    promptPolicy: 'Prompt Politikası',
    mfa: 'MFA',
    apiKeys: 'API Keys',
    sessions: 'Aktif Oturum Politikası',
    health: 'Sistem Sağlığı',
    license: 'Lisans',
    aiUsage: 'AI Kullanımı',
    storage: 'Depolama',
    activeUsers: 'Aktif Kullanıcı',
    roles: 'Roller',
    none: '—',
    dash: '—',
    notConfigured: 'Yapılandırılmadı',
    notConnected: 'Bağlı Değil',
    connected: 'Bağlı',
    active: 'Aktif',
    closed: 'Kapalı',
    error: 'Hata',
    running: 'Çalışıyor',
    issue: 'Sorun Var',
    unknown: 'Bilinmiyor',
    healthUnavailable: 'Durum bilgisi mevcut değil',
    licenseUnavailable: 'Lisans bilgisi mevcut değil',
    aiUsageUnavailable: 'AI kullanım verisi mevcut değil',
    storageUnavailable: 'Depolama bilgisi mevcut değil',
    aiUnavailable: 'Yapılandırılmadı',
    accessDenied: 'Ayarları görüntüleme yetkiniz yok.',
    tabs: {
      general: 'Genel',
      crm: 'CRM',
      ai: 'AI',
      users: 'Kullanıcılar & Roller',
      notifications: 'Bildirimler',
      integrations: 'Entegrasyonlar',
      security: 'Güvenlik',
      system: 'Sistem',
      billing: 'Faturalama',
    } as Record<TabId, string>,
    providers: {
      local_ai: 'Yerel AI',
      openai: 'OpenAI',
      local_ocr: 'Yerel OCR',
      local_storage: 'Yerel depolama',
      s3: 'Amazon S3',
      gmail: 'Gmail',
    } as Record<string, string>,
    languages: { tr: 'Türkçe', en: 'English' } as Record<string, string>,
    keysCount: '{count} aktif anahtar',
    usersCount: '{count} kullanıcı',
    rolesCount: '{count} rol',
    stageCount: '{count}',
    manageSecurity: 'Güvenliği Yönet',
  },
  en: {
    title: 'Settings',
    subtitle: 'Manage system configuration and connections.',
    commAccounts: 'Communication accounts',
    history: 'Change history',
    editSettings: 'Edit settings',
    edit: 'Edit',
    manage: 'Manage',
    connect: 'Connect',
    details: 'View details',
    general: 'General settings',
    crm: 'CRM configuration',
    notifications: 'Notification channels',
    ai: 'AI configuration',
    integrations: 'Integrations',
    security: 'Security',
    users: 'Users & roles',
    billing: 'Billing',
    company: 'Company',
    language: 'Language',
    timezone: 'Timezone',
    companyId: 'Company ID',
    logo: 'Logo',
    lastUpdated: 'Last updated',
    pipeline: 'Pipeline stages',
    opportunity: 'Opportunity stages',
    activityTypes: 'Activity types',
    taskTypes: 'Task types',
    tags: 'Tags',
    email: 'Email',
    whatsapp: 'WhatsApp',
    sms: 'SMS',
    gmail: 'Gmail',
    provider: 'Provider',
    model: 'Model',
    promptPolicy: 'Prompt policy',
    mfa: 'MFA',
    apiKeys: 'API keys',
    sessions: 'Active session policy',
    health: 'System health',
    license: 'License',
    aiUsage: 'AI usage',
    storage: 'Storage',
    activeUsers: 'Active users',
    roles: 'Roles',
    none: '—',
    dash: '—',
    notConfigured: 'Not configured',
    notConnected: 'Not connected',
    connected: 'Connected',
    active: 'Active',
    closed: 'Off',
    error: 'Error',
    running: 'Running',
    issue: 'Issue',
    unknown: 'Unknown',
    healthUnavailable: 'Status information is not available',
    licenseUnavailable: 'License information is not available',
    aiUsageUnavailable: 'AI usage data is not available',
    storageUnavailable: 'Storage information is not available',
    aiUnavailable: 'Not configured',
    accessDenied: 'You do not have permission to view settings.',
    tabs: {
      general: 'General',
      crm: 'CRM',
      ai: 'AI',
      users: 'Users & roles',
      notifications: 'Notifications',
      integrations: 'Integrations',
      security: 'Security',
      system: 'System',
      billing: 'Billing',
    } as Record<TabId, string>,
    providers: {
      local_ai: 'Local AI',
      openai: 'OpenAI',
      local_ocr: 'Local OCR',
      local_storage: 'Local storage',
      s3: 'Amazon S3',
      gmail: 'Gmail',
    } as Record<string, string>,
    languages: { tr: 'Turkish', en: 'English' } as Record<string, string>,
    keysCount: '{count} active keys',
    usersCount: '{count} users',
    rolesCount: '{count} roles',
    stageCount: '{count}',
    manageSecurity: 'Manage security',
  },
};

function formatWhen(value: string | null | undefined, locale: string) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function initials(name: string | null | undefined) {
  const parts = (name ?? '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return 'IH';
  return parts
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

function secretPref(item: PreferenceItem) {
  return item.is_secret || /secret|token|password|key|credential/i.test(item.preference_key);
}

function prefText(items: PreferenceItem[] | undefined, keyPart: string) {
  const item = (items ?? []).find(
    (row) => !secretPref(row) && row.is_configured && row.preference_key.toLowerCase().includes(keyPart),
  );
  if (!item) return null;
  if (typeof item.value === 'string' || typeof item.value === 'number') return String(item.value);
  return null;
}

function providerLabel(id: string, labels: Record<string, string>) {
  return labels[id] ?? id.replace(/_/g, ' ');
}

function mapProviderTone(status: string, configured: boolean): { labelKey: 'connected' | 'notConnected' | 'notConfigured' | 'error' | 'active'; tone: BadgeTone } {
  const normalized = status.toLowerCase();
  if (normalized.includes('error') || normalized === 'unavailable') return { labelKey: 'error', tone: 'danger' };
  if (normalized === 'not_connected' || normalized === 'disconnected') return { labelKey: 'notConnected', tone: 'warn' };
  if (normalized === 'not_configured' || (!configured && normalized !== 'ready')) return { labelKey: 'notConfigured', tone: 'warn' };
  if (normalized === 'connected') return { labelKey: 'connected', tone: 'ok' };
  if (configured || normalized === 'ready' || normalized === 'configured' || normalized === 'healthy') {
    return { labelKey: 'active', tone: 'ok' };
  }
  return { labelKey: 'notConfigured', tone: 'warn' };
}

function mapHealth(status: string): { labelKey: 'running' | 'issue' | 'unknown'; tone: BadgeTone } {
  const normalized = status.toLowerCase();
  if (['healthy', 'ok', 'ready', 'configured', 'running'].includes(normalized)) return { labelKey: 'running', tone: 'ok' };
  if (['degraded', 'unavailable', 'error', 'down'].includes(normalized)) return { labelKey: 'issue', tone: 'danger' };
  return { labelKey: 'unknown', tone: 'warn' };
}

function ActionLink({ href, children, primary = false }: { href: string; children: ReactNode; primary?: boolean }) {
  return (
    <Link
      href={href as Route}
      className={primary ? 'ih-btn ih-btn--primary ih-btn--sm' : 'ih-btn ih-btn--secondary ih-btn--sm'}
    >
      {children}
    </Link>
  );
}

function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return <span className={`crm-ops-badge is-${tone}`}>{children}</span>;
}

function Card({
  title,
  icon,
  action,
  children,
}: {
  title: string;
  icon: IhIconName;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <article className="crm-ops-card">
      <header className="crm-ops-card__head">
        <h2 className="crm-ops-card__title">
          <span aria-hidden>
            <IhIcon name={icon} size={14} />
          </span>
          {title}
        </h2>
        {action}
      </header>
      {children}
    </article>
  );
}

export function CrmSettingsLiveWorkspace() {
  const locale = useLocale();
  const copy = locale.startsWith('en') ? COPY.en : COPY.tr;
  const { authLoading, user, canRead } = useCrmAccess();
  const [tab, setTab] = useState<TabId>('general');
  const canView = Boolean(user && (canRead || hasPermission(user, 'settings', 'view')));

  const companyQuery = useQuery({
    queryKey: ['company', 'profile'],
    queryFn: fetchCompanyProfile,
    enabled: !authLoading && canView,
    retry: false,
  });
  const brandsQuery = useQuery({
    queryKey: ['company', 'brands'],
    queryFn: () => fetchBrands(),
    enabled: !authLoading && canView,
    retry: false,
  });
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
  const providersQuery = useQuery({
    queryKey: ['settings', 'providers'],
    queryFn: fetchProviderStatuses,
    enabled: !authLoading && canView,
    retry: false,
  });
  const preferencesQuery = useQuery({
    queryKey: ['settings', 'preferences'],
    queryFn: fetchPreferences,
    enabled: !authLoading && canView,
    retry: false,
  });
  const healthQuery = useQuery({
    queryKey: ['security', 'health'],
    queryFn: fetchSystemHealth,
    enabled: !authLoading && canView,
    retry: false,
  });
  const mfaQuery = useQuery({
    queryKey: ['security', 'mfa'],
    queryFn: fetchMfaPolicy,
    enabled: !authLoading && canView,
    retry: false,
  });
  const keysQuery = useQuery({
    queryKey: ['security', 'api-keys'],
    queryFn: fetchApiKeys,
    enabled: !authLoading && canView,
    retry: false,
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'active-settings'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canView,
    retry: false,
  });
  const rolesQuery = useQuery({
    queryKey: ['roles', 'settings'],
    queryFn: fetchRoles,
    enabled: !authLoading && canView,
    retry: false,
  });

  const company = companyQuery.data;
  const brand = (brandsQuery.data ?? []).find((item) => item.is_default) ?? brandsQuery.data?.[0] ?? null;
  const accounts = accountsQuery.data?.items ?? [];
  const providers = providersQuery.data?.items ?? [];
  const prefs = preferencesQuery.data;
  const health = healthQuery.data;

  const emailConnected = accounts.some(
    (item) => item.channel_type === 'email' && item.status === 'connected',
  );
  const whatsappConnected = accounts.some(
    (item) => item.channel_type === 'whatsapp' && item.status === 'connected',
  );
  const gmailConnected = (gmailQuery.data?.connected_count ?? 0) > 0 || accounts.some(
    (item) => item.provider === 'gmail' && item.status === 'connected',
  );

  const logoText = initials(brand?.brand_name || company?.short_name || company?.company_name);
  const language = company?.default_language
    ? copy.languages[company.default_language] ?? company.default_language
    : copy.none;
  const updated = formatWhen(company?.updated_at, locale) ?? copy.none;

  const aiHealth = health?.components.find((item) => item.id === 'ai');
  const aiProviderName = aiHealth?.detail?.replace(/^Provider:\s*/i, '').trim() || null;
  const aiPrefModel = prefText(prefs?.categories.ai, 'model');
  const openai = providers.find((item) => item.provider_id === 'openai');
  const localAi = providers.find((item) => item.provider_id === 'local_ai');
  const shownAiProvider = openai?.configured
    ? copy.providers.openai
    : localAi
      ? copy.providers.local_ai
      : aiProviderName
        ? providerLabel(aiProviderName, copy.providers)
        : null;

  const activeKeyCount = (keysQuery.data?.items ?? []).filter((item) => item.status === 'active').length;
  const mfaOn =
    mfaQuery.data?.enforcement === 'required' ||
    mfaQuery.data?.enforcement === 'enabled' ||
    mfaQuery.data?.methods.some((item) => item.configured && item.status !== 'not_configured');

  const crmRows = useMemo(
    () => [
      {
        id: 'pipeline',
        icon: 'barChart' as const,
        title: copy.pipeline,
        value: copy.none,
        href: '/workspaces/crm/pipeline',
      },
      {
        id: 'opportunity',
        icon: 'target' as const,
        title: copy.opportunity,
        value: copy.none,
        href: '/workspaces/crm/agreements',
      },
      {
        id: 'activity',
        icon: 'activity' as const,
        title: copy.activityTypes,
        value: copy.none,
        href: '/workspaces/crm/communication',
      },
      {
        id: 'tasks',
        icon: 'check' as const,
        title: copy.taskTypes,
        value: copy.none,
        href: '/workspaces/crm/tasks',
      },
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

  const notifyRows = [
    {
      id: 'email',
      icon: 'mail' as const,
      title: copy.email,
      connected: emailConnected || gmailConnected,
    },
    {
      id: 'whatsapp',
      icon: 'phone' as const,
      title: copy.whatsapp,
      connected: whatsappConnected,
    },
    {
      id: 'sms',
      icon: 'bell' as const,
      title: copy.sms,
      connected: false,
      configured: Boolean(prefText(prefs?.categories.notifications, 'sms')),
    },
  ];

  const integrationRows: Array<{
    id: string;
    title: string;
    status: ReturnType<typeof mapProviderTone>;
    href: string;
    connect?: boolean;
  }> = [
    ...(providers as ProviderStatus[]).map((item) => ({
      id: item.provider_id,
      title: providerLabel(item.provider_id, copy.providers),
      status: mapProviderTone(item.status, item.configured),
      href:
        item.category === 'ai'
          ? '/dashboard/settings?tab=ai'
          : item.category === 'storage'
            ? '/dashboard/settings?tab=storage'
            : '/dashboard/settings?tab=integrations',
    })),
    {
      id: 'gmail',
      title: copy.gmail,
      status: gmailConnected
        ? { labelKey: 'connected' as const, tone: 'ok' as const }
        : gmailQuery.data && !gmailQuery.data.configured
          ? { labelKey: 'notConfigured' as const, tone: 'warn' as const }
          : { labelKey: 'notConnected' as const, tone: 'warn' as const },
      href: '/workspaces/crm/settings/communication-accounts',
      connect: !gmailConnected,
    },
  ];

  const onOverview = tab === 'general';
  const showCard = (id: TabId) => {
    if (tab === id) return true;
    if (!onOverview) return false;
    return id === 'general' || id === 'crm' || id === 'notifications' || id === 'ai' || id === 'integrations' || id === 'security';
  };
  const showRail = onOverview || tab === 'system' || tab === 'ai';

  if (authLoading || (canView && companyQuery.isLoading && !companyQuery.data)) {
    return <LoadingState />;
  }
  if (!canView) {
    return <ErrorState title={copy.title} message={copy.accessDenied} />;
  }

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
          <ActionLink href="/dashboard/admin/audit">{copy.history}</ActionLink>
          <ActionLink href="/dashboard/settings" primary>
            {copy.editSettings}
          </ActionLink>
        </div>
      </header>

      <nav className="crm-ops-tabs" aria-label={copy.title}>
        {TABS.map((id) => (
          <button
            key={id}
            type="button"
            className={tab === id ? 'is-active' : undefined}
            onClick={() => setTab(id)}
          >
            {copy.tabs[id]}
          </button>
        ))}
      </nav>

      <div className="crm-ops-settings-layout">
        <div className="crm-ops-settings-main">
          <div className="crm-ops-settings-col">
            {showCard('general') ? (
              <Card
                title={copy.general}
                icon="settings"
                action={<ActionLink href="/dashboard/settings?tab=company">{copy.edit}</ActionLink>}
              >
                {company ? (
                  <dl className="crm-ops-kv">
                    <div>
                      <dt>{copy.company}</dt>
                      <dd>{company.company_name || copy.none}</dd>
                    </div>
                    <div>
                      <dt>{copy.language}</dt>
                      <dd>{language}</dd>
                    </div>
                    <div>
                      <dt>{copy.timezone}</dt>
                      <dd>{company.default_timezone || copy.none}</dd>
                    </div>
                    <div>
                      <dt>{copy.companyId}</dt>
                      <dd className={company.company_code ? undefined : 'is-secondary'}>
                        {company.company_code || copy.none}
                      </dd>
                    </div>
                    <div>
                      <dt>{copy.logo}</dt>
                      <dd>
                        <span className="crm-ops-logo">{logoText}</span>
                      </dd>
                    </div>
                    <div>
                      <dt>{copy.lastUpdated}</dt>
                      <dd>{updated}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="crm-ops-empty">{copy.none}</p>
                )}
              </Card>
            ) : null}

            {showCard('crm') ? (
              <Card title={copy.crm} icon="crm">
                <ul className="crm-ops-rows">
                  {crmRows.map((row) => (
                    <li key={row.id} className="crm-ops-row">
                      <span className="crm-ops-row__icon" aria-hidden>
                        <IhIcon name={row.icon} size={13} />
                      </span>
                      <span className="crm-ops-row__copy">
                        <strong>{row.title}</strong>
                      </span>
                      <em className="crm-ops-row__meta">{row.value}</em>
                      <ActionLink href={row.href}>{copy.manage}</ActionLink>
                    </li>
                  ))}
                </ul>
              </Card>
            ) : null}

            {showCard('notifications') ? (
              <Card
                title={copy.notifications}
                icon="bell"
                action={<ActionLink href="/dashboard/settings?tab=notifications">{copy.manage}</ActionLink>}
              >
                <ul className="crm-ops-rows">
                  {notifyRows.map((row) => (
                    <li key={row.id} className="crm-ops-row">
                      <span className="crm-ops-row__icon" aria-hidden>
                        <IhIcon name={row.icon} size={13} />
                      </span>
                      <span className="crm-ops-row__copy">
                        <strong>{row.title}</strong>
                      </span>
                      <Badge tone={row.connected ? 'ok' : 'warn'}>
                        {row.connected ? copy.connected : row.configured ? copy.closed : copy.notConnected}
                      </Badge>
                      <ActionLink href="/workspaces/crm/settings/communication-accounts">{copy.manage}</ActionLink>
                    </li>
                  ))}
                </ul>
              </Card>
            ) : null}

            {showCard('users') ? (
              <Card
                title={copy.users}
                icon="users"
                action={<ActionLink href="/dashboard/admin/users">{copy.manage}</ActionLink>}
              >
                <ul className="crm-ops-rows">
                  <li className="crm-ops-row">
                    <span className="crm-ops-row__icon" aria-hidden>
                      <IhIcon name="user" size={13} />
                    </span>
                    <span className="crm-ops-row__copy">
                      <strong>{copy.activeUsers}</strong>
                    </span>
                    <em className="crm-ops-row__meta">
                      {usersQuery.data
                        ? copy.usersCount.replace('{count}', String(usersQuery.data.total ?? usersQuery.data.items.length))
                        : copy.none}
                    </em>
                    <ActionLink href="/dashboard/admin/users">{copy.manage}</ActionLink>
                  </li>
                  <li className="crm-ops-row">
                    <span className="crm-ops-row__icon" aria-hidden>
                      <IhIcon name="roles" size={13} />
                    </span>
                    <span className="crm-ops-row__copy">
                      <strong>{copy.roles}</strong>
                    </span>
                    <em className="crm-ops-row__meta">
                      {rolesQuery.data
                        ? copy.rolesCount.replace('{count}', String(rolesQuery.data.total ?? rolesQuery.data.items.length))
                        : copy.none}
                    </em>
                    <ActionLink href="/dashboard/admin/users">{copy.manage}</ActionLink>
                  </li>
                </ul>
              </Card>
            ) : null}
          </div>

          <div className="crm-ops-settings-col">
            {showCard('ai') ? (
              <Card
                title={copy.ai}
                icon="sparkles"
                action={<ActionLink href="/dashboard/settings?tab=ai">{copy.edit}</ActionLink>}
              >
                {shownAiProvider || aiPrefModel ? (
                  <dl className="crm-ops-kv">
                    <div>
                      <dt>{copy.provider}</dt>
                      <dd>{shownAiProvider ?? copy.none}</dd>
                    </div>
                    <div>
                      <dt>{copy.model}</dt>
                      <dd>{aiPrefModel ?? copy.none}</dd>
                    </div>
                    <div>
                      <dt>{copy.language}</dt>
                      <dd>{language}</dd>
                    </div>
                    <div>
                      <dt>{copy.promptPolicy}</dt>
                      <dd>{prefText(prefs?.categories.ai, 'prompt') ?? copy.notConfigured}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="crm-ops-empty">{copy.aiUnavailable}</p>
                )}
              </Card>
            ) : null}

            {showCard('integrations') ? (
              <Card
                title={copy.integrations}
                icon="inbox"
                action={<ActionLink href="/dashboard/settings?tab=integrations">{copy.manage}</ActionLink>}
              >
                {integrationRows.length ? (
                  <ul className="crm-ops-rows">
                    {integrationRows.map((row) => (
                      <li key={row.id} className="crm-ops-row">
                        <span className="crm-ops-mark" aria-hidden>
                          {row.title.slice(0, 1).toUpperCase()}
                        </span>
                        <span className="crm-ops-row__copy">
                          <strong>{row.title}</strong>
                        </span>
                        <Badge tone={row.status.tone}>{copy[row.status.labelKey]}</Badge>
                        <ActionLink href={row.href}>{row.connect ? copy.connect : copy.manage}</ActionLink>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="crm-ops-empty">{copy.notConfigured}</p>
                )}
              </Card>
            ) : null}

            {showCard('security') ? (
              <Card
                title={copy.security}
                icon="permissions"
                action={<ActionLink href="/dashboard/admin/security">{copy.manageSecurity}</ActionLink>}
              >
                <ul className="crm-ops-rows">
                  <li className="crm-ops-row">
                    <span className="crm-ops-row__icon" aria-hidden>
                      <IhIcon name="permissions" size={13} />
                    </span>
                    <span className="crm-ops-row__copy">
                      <strong>{copy.mfa}</strong>
                    </span>
                    {mfaQuery.data ? (
                      <Badge tone={mfaOn ? 'ok' : 'warn'}>{mfaOn ? copy.active : copy.notConfigured}</Badge>
                    ) : (
                      <em className="crm-ops-row__meta">{copy.none}</em>
                    )}
                    <ActionLink href="/dashboard/admin/authentication">{copy.manage}</ActionLink>
                  </li>
                  <li className="crm-ops-row">
                    <span className="crm-ops-row__icon" aria-hidden>
                      <IhIcon name="settings" size={13} />
                    </span>
                    <span className="crm-ops-row__copy">
                      <strong>{copy.apiKeys}</strong>
                    </span>
                    <em className="crm-ops-row__meta">
                      {keysQuery.data
                        ? copy.keysCount.replace('{count}', String(activeKeyCount))
                        : copy.none}
                    </em>
                    <ActionLink href="/dashboard/admin/api-keys">{copy.manage}</ActionLink>
                  </li>
                </ul>
              </Card>
            ) : null}

            {showCard('system') ? (
              <Card
                title={copy.health}
                icon="activity"
                action={<ActionLink href="/dashboard/admin/system">{copy.details}</ActionLink>}
              >
                {health?.components?.length ? (
                  <ul className="crm-ops-health">
                    {health.components.map((item) => {
                      const mapped = mapHealth(item.status);
                      return (
                        <li key={item.id}>
                          <i className={`is-${mapped.tone}`} aria-hidden />
                          <strong>{item.label}</strong>
                          <Badge tone={mapped.tone}>{copy[mapped.labelKey]}</Badge>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="crm-ops-empty">{copy.healthUnavailable}</p>
                )}
              </Card>
            ) : null}

            {showCard('billing') ? (
              <Card title={copy.license} icon="documents">
                <p className="crm-ops-empty">{copy.licenseUnavailable}</p>
              </Card>
            ) : null}
          </div>
        </div>

        {showRail ? (
          <aside className="crm-ops-settings-rail" aria-label={copy.health}>
            {tab === 'general' || tab === 'system' ? (
              <Card
                title={copy.health}
                icon="activity"
                action={<ActionLink href="/dashboard/admin/system">{copy.details}</ActionLink>}
              >
                {health?.components?.length ? (
                  <ul className="crm-ops-health">
                    {health.components.map((item) => {
                      const mapped = mapHealth(item.status);
                      return (
                        <li key={item.id}>
                          <i className={`is-${mapped.tone}`} aria-hidden />
                          <strong>{item.label}</strong>
                          <span className={`crm-ops-badge is-${mapped.tone}`}>{copy[mapped.labelKey]}</span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="crm-ops-empty">{copy.healthUnavailable}</p>
                )}
              </Card>
            ) : null}

            {tab === 'general' || tab === 'billing' ? (
              <Card title={copy.license} icon="documents">
                <p className="crm-ops-empty">{copy.licenseUnavailable}</p>
              </Card>
            ) : null}

            {tab === 'general' || tab === 'ai' ? (
              <Card title={copy.aiUsage} icon="sparkles">
                <p className="crm-ops-empty">{copy.aiUsageUnavailable}</p>
              </Card>
            ) : null}

            {tab === 'general' || tab === 'system' ? (
              <Card
                title={copy.storage}
                icon="documents"
                action={<ActionLink href="/dashboard/settings?tab=storage">{copy.details}</ActionLink>}
              >
                <p className="crm-ops-empty">{copy.storageUnavailable}</p>
              </Card>
            ) : null}
          </aside>
        ) : null}
      </div>
    </div>
  );
}
