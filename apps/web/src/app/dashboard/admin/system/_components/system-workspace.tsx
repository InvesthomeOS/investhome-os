'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  fetchBackupStatus,
  fetchFeatureFlags,
  fetchSystemConfig,
  fetchSystemHealth,
  updateFeatureFlag,
  type FeatureFlagItem,
  type SystemHealth,
} from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { SecSection, StatusBadge } from '../../_components/sec-ui';
import { useAdminToast } from '../../_components/use-admin-toast';

function backupToneStatus(status: string): string {
  return status === 'configured' ? 'not_verified' : status;
}

export function SystemWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { notifySuccess, notifyError } = useAdminToast();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [flags, setFlags] = useState<FeatureFlagItem[]>([]);
  const [currencies, setCurrencies] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);
  const [timezones, setTimezones] = useState<string[]>([]);
  const [backup, setBackup] = useState<{
    status: string;
    health: string;
    provider: string;
    message: string;
    last_backup_at: string | null;
    restore_verified: boolean;
    warning: boolean;
    env_keys: string[];
  } | null>(null);
  const canUpdate = Boolean(user && hasPermission(user, 'settings', 'update'));

  const load = useCallback(async () => {
    const [h, f, cfg, b] = await Promise.all([
      fetchSystemHealth(),
      fetchFeatureFlags(),
      fetchSystemConfig(),
      fetchBackupStatus(),
    ]);
    setHealth(h);
    setFlags(f.items);
    setCurrencies(cfg.currencies);
    setLanguages(cfg.languages);
    setTimezones(cfg.timezones);
    setBackup(b);
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (
      !hasPermission(user, 'security', 'view') &&
      !hasPermission(user, 'settings', 'view')
    ) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [authLoading, load, router, user]);

  return (
    <main className="dashboard" data-sec-workspace="system">
      <PageHeader eyebrow={t('eyebrow')} title={t('systemTitle')} subtitle={t('systemSubtitle')} />
      <SecSection
        title={t('healthTitle')}
        description={health ? t('healthOverall', { status: health.overall }) : undefined}
      >
        <div className="sec-card-grid">
          {(health?.components ?? []).map((c) => (
            <article key={c.id} className="sec-card">
              <h3>{c.label}</h3>
              <StatusBadge status={c.status} />
              <p>{c.detail ?? '—'}</p>
              {c.link ? <Link href={c.link as '/dashboard/automation'}>{t('openLink')}</Link> : null}
            </article>
          ))}
        </div>
      </SecSection>
      <SecSection title={t('backupTitle')}>
        {backup ? (
          <div
            className="sec-card"
            data-testid="backup-status-card"
            data-backup-warning={backup.warning ? 'true' : 'false'}
          >
            <StatusBadge status={backupToneStatus(backup.status)}>{backup.status.replace(/_/g, ' ')}</StatusBadge>
            <p>
              {t('backupHealth')}: <StatusBadge status={backup.health} />
            </p>
            <p>
              {t('backupProvider')}: {backup.provider}
            </p>
            <p>
              {t('lastBackup')}:{' '}
              {backup.last_backup_at ? new Date(backup.last_backup_at).toLocaleString() : t('never')}
            </p>
            {backup.warning ? (
              <p className="sec-note" data-testid="backup-status-warning">
                {t('backupStatusWarning')}
              </p>
            ) : null}
            <p className="sec-note">{backup.message}</p>
            <code className="sec-code">{backup.env_keys.join(', ')}</code>
          </div>
        ) : null}
      </SecSection>
      <SecSection title={t('featureFlagsTitle')} description={t('featureFlagsSubtitle')}>
        <div className="sec-table-wrap">
          <table className="sec-table">
            <thead>
              <tr>
                <th>{t('colFlag')}</th>
                <th>{t('colSource')}</th>
                <th>{t('colEnabled')}</th>
                <th>{t('colRollout')}</th>
                <th>{t('colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {flags.map((flag) => (
                <tr key={flag.key}>
                  <td>
                    <code>{flag.key}</code>
                  </td>
                  <td>{flag.source}</td>
                  <td>
                    <StatusBadge status={flag.enabled ? 'enabled' : 'disabled'} />
                  </td>
                  <td>{flag.rollout_percent}%</td>
                  <td>
                    {canUpdate ? (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={async () => {
                          try {
                            await updateFeatureFlag(flag.key, {
                              enabled: !flag.enabled,
                              rollout_percent: flag.rollout_percent,
                              target_roles: flag.target_roles,
                            });
                            notifySuccess(t('flagUpdated'));
                            await load();
                          } catch (err) {
                            notifyError(err, t('saveFailed'));
                          }
                        }}
                      >
                        {flag.enabled ? t('disable') : t('enable')}
                      </Button>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SecSection>
      <SecSection title={t('localeConfigTitle')}>
        <p>
          <strong>{t('currencies')}:</strong> {currencies.slice(0, 12).join(', ')}
          {currencies.length > 12 ? '…' : ''}
        </p>
        <p>
          <strong>{t('languages')}:</strong> {languages.join(', ')}
        </p>
        <p>
          <strong>{t('timezones')}:</strong> {timezones.join(', ')}
        </p>
        <p>
          <Link href="/dashboard/settings">{t('openSettings')}</Link>
        </p>
      </SecSection>
    </main>
  );
}
