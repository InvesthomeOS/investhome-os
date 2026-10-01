'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { apiFetch, unwrapApiEnvelope, type ApiEnvelope } from '@/lib/api/client';
import { fetchHealth } from '@/lib/api/health';
import {
  fetchBackupStatus,
  fetchFeatureFlags,
  fetchSystemHealth,
  type FeatureFlagItem,
  type SystemHealth,
} from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { SecSection, StatusBadge } from '../../_components/sec-ui';

type ProbeResult = {
  id: string;
  label: string;
  status: 'ok' | 'warn' | 'fail' | 'unavailable';
  detail: string;
};

type MetaPayload = {
  service?: string;
  version?: string;
  environment?: string;
  feature_flags?: Record<string, boolean>;
};

function classify(status: string): 'ok' | 'warn' | 'fail' | 'unavailable' {
  const s = status.toLowerCase();
  if (['healthy', 'ok', 'ready', 'alive', 'verified', 'active'].includes(s)) return 'ok';
  if (['degraded', 'not_configured', 'configured', 'stale', 'warning', 'missing', 'disabled', 'unknown'].includes(s)) {
    return 'warn';
  }
  if (['unavailable', 'not_ready', 'invalid', 'error', 'fail', 'failed'].includes(s)) return 'fail';
  return 'unavailable';
}

function classifyBackup(status: string | undefined): 'ok' | 'warn' | 'fail' | 'unavailable' {
  if (!status) return 'unavailable';
  if (status === 'verified') return 'ok';
  if (status === 'failed') return 'fail';
  return 'warn';
}

function backupToneStatus(status: string): string {
  return status === 'configured' ? 'not_verified' : status;
}

export function LaunchHealthWorkspace() {
  const t = useTranslations('adminLaunchHealth');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [backup, setBackup] = useState<{
    status: string;
    health: string;
    provider: string;
    message: string;
    last_backup_at: string | null;
    restore_verified: boolean;
    warning: boolean;
  } | null>(null);
  const [flags, setFlags] = useState<FeatureFlagItem[]>([]);
  const [probes, setProbes] = useState<ProbeResult[]>([]);
  const [meta, setMeta] = useState<MetaPayload | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canView =
    Boolean(user) &&
    (hasPermission(user, 'security', 'view') || hasPermission(user, 'settings', 'view'));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [systemHealthRes, backupRes, featureFlagsRes, publicHealthRes, metaRes] =
        await Promise.allSettled([
          fetchSystemHealth(),
          fetchBackupStatus(),
          fetchFeatureFlags(),
          fetchHealth(),
          apiFetch<ApiEnvelope<MetaPayload>>('/meta'),
        ]);

      const systemHealth = systemHealthRes.status === 'fulfilled' ? systemHealthRes.value : null;
      const backupStatus = backupRes.status === 'fulfilled' ? backupRes.value : null;
      const featureFlags = featureFlagsRes.status === 'fulfilled' ? featureFlagsRes.value : null;
      const publicHealth = publicHealthRes.status === 'fulfilled' ? publicHealthRes.value : null;
      const metaData =
        metaRes.status === 'fulfilled' ? unwrapApiEnvelope(metaRes.value) : null;

      setHealth(systemHealth);
      setBackup(backupStatus);
      setFlags(featureFlags?.items ?? []);
      setMeta(metaData);

      const envLabel = publicHealth?.environment ?? metaData?.environment ?? 'unknown';
      const nextProbes: ProbeResult[] = [
        {
          id: 'env',
          label: t('probeEnvironment'),
          status: envLabel === 'production' ? 'ok' : 'warn',
          detail:
            envLabel === 'production'
              ? t('probeEnvironmentProduction')
              : t('probeEnvironmentNotProduction', { environment: envLabel }),
        },
        {
          id: 'api-health',
          label: t('probeApiHealth'),
          status: publicHealth?.status === 'ok' ? 'ok' : 'fail',
          detail: publicHealth
            ? `${publicHealth.service ?? 'API'} ${publicHealth.version ?? ''} · db=${publicHealth.database}`
            : t('unavailable'),
        },
        {
          id: 'system-overall',
          label: t('probeSystemOverall'),
          status: systemHealth ? classify(systemHealth.overall) : 'unavailable',
          detail: systemHealth?.overall ?? t('unavailable'),
        },
        {
          id: 'backup',
          label: t('probeBackup'),
          status: classifyBackup(backupStatus?.status),
          detail: backupStatus
            ? `${backupStatus.provider} · ${backupStatus.status} · ${backupStatus.message}`
            : t('unavailable'),
        },
        {
          id: 'hosting',
          label: t('probeHosting'),
          status: 'unavailable',
          detail: t('probeHostingDetail'),
        },
        {
          id: 'observability',
          label: t('probeObservability'),
          status: 'unavailable',
          detail: t('probeObservabilityDetail'),
        },
        {
          id: 'alerting',
          label: t('probeAlerting'),
          status: 'unavailable',
          detail: t('probeAlertingDetail'),
        },
      ];
      setProbes(nextProbes);
      setRefreshedAt(new Date().toISOString());
      if (!publicHealth && !systemHealth) {
        setError(t('loadFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!canView) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [authLoading, canView, load, router, user]);

  if (authLoading || !user || !canView) {
    return null;
  }

  const criticalFail = probes.some((p) => p.id === 'backup' || p.id === 'hosting') &&
    probes.some((p) => p.status === 'fail' || p.status === 'unavailable');

  return (
    <main className="dashboard" data-sec-workspace="launch-health" data-testid="launch-health">
      <PageHeader eyebrow={t('eyebrow')} title={t('title')} subtitle={t('subtitle')} />

      <div className="sec-card" data-launch-banner="env">
        <StatusBadge status={criticalFail ? 'not_ready' : health?.overall ?? 'unknown'} />
        <p className="sec-note">{t('localOnlyBanner')}</p>
        <p>
          {t('refreshedAt')}: {refreshedAt ? new Date(refreshedAt).toLocaleString() : '—'}
        </p>
        <Button type="button" variant="secondary" onClick={() => void load()} disabled={loading}>
          {loading ? t('refreshing') : t('refresh')}
        </Button>
      </div>

      {error ? <p className="sec-note">{error}</p> : null}

      <SecSection title={t('goNoGoTitle')} description={t('goNoGoSubtitle')}>
        <div className="sec-card-grid">
          {probes.map((probe) => (
            <article key={probe.id} className="sec-card" data-probe={probe.id}>
              <h3>{probe.label}</h3>
              <StatusBadge
                status={
                  probe.status === 'ok'
                    ? 'healthy'
                    : probe.status === 'warn'
                      ? 'degraded'
                      : probe.status === 'fail'
                        ? 'unavailable'
                        : 'not_configured'
                }
              />
              <p>{probe.detail}</p>
            </article>
          ))}
        </div>
      </SecSection>

      <SecSection title={t('runtimeTitle')} description={t('runtimeSubtitle')}>
        <div className="sec-card-grid">
          <article className="sec-card">
            <h3>{t('metaService')}</h3>
            <p>{meta?.service ?? '—'}</p>
            <p>
              {t('metaVersion')}: {meta?.version ?? '—'}
            </p>
            <p>
              {t('metaEnvironment')}: {meta?.environment ?? '—'}
            </p>
          </article>
          {(health?.components ?? []).map((c) => (
            <article key={c.id} className="sec-card">
              <h3>{c.label}</h3>
              <StatusBadge status={c.status} />
              <p>{c.detail ?? '—'}</p>
              {c.link?.startsWith('/dashboard') ? (
                <Link href={c.link as '/dashboard/automation'}>{t('openLink')}</Link>
              ) : null}
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
              {t('backupProvider')}: {backup.provider}
            </p>
            <p>
              {t('backupHealth')}: <StatusBadge status={backup.health} />
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
            <p className="sec-note">{t('backupRestoreUnverified')}</p>
          </div>
        ) : (
          <p className="sec-empty">{t('unavailable')}</p>
        )}
      </SecSection>

      <SecSection title={t('integrationsTitle')} description={t('integrationsSubtitle')}>
        <div className="sec-card-grid">
          <article className="sec-card">
            <h3>{t('integrationSentry')}</h3>
            <StatusBadge status="not_configured" />
            <p>{t('integrationUnavailable')}</p>
          </article>
          <article className="sec-card">
            <h3>{t('integrationPrometheus')}</h3>
            <StatusBadge status="not_configured" />
            <p>{t('integrationUnavailable')}</p>
          </article>
          <article className="sec-card">
            <h3>{t('integrationPager')}</h3>
            <StatusBadge status="not_configured" />
            <p>{t('integrationUnavailable')}</p>
          </article>
          <article className="sec-card">
            <h3>{t('integrationSmtp')}</h3>
            <StatusBadge status="not_configured" />
            <p>{t('integrationSmtpDetail')}</p>
          </article>
          <article className="sec-card">
            <h3>{t('integrationExternalAi')}</h3>
            <StatusBadge
              status={
                flags.find((f) => f.key === 'external_ai')?.enabled ? 'configured' : 'disabled'
              }
            />
            <p>{t('integrationExternalAiDetail')}</p>
          </article>
          <article className="sec-card">
            <h3>{t('integrationN8n')}</h3>
            <StatusBadge
              status={
                flags.find((f) => f.key === 'n8n_automation')?.enabled ? 'configured' : 'disabled'
              }
            />
            <p>{t('integrationN8nDetail')}</p>
          </article>
        </div>
      </SecSection>

      <SecSection title={t('flagsTitle')}>
        <div className="sec-table-wrap">
          <table className="sec-table">
            <thead>
              <tr>
                <th>{t('colFlag')}</th>
                <th>{t('colEnabled')}</th>
                <th>{t('colSource')}</th>
              </tr>
            </thead>
            <tbody>
              {flags.map((flag) => (
                <tr key={flag.key}>
                  <td>
                    <code>{flag.key}</code>
                  </td>
                  <td>
                    <StatusBadge status={flag.enabled ? 'enabled' : 'disabled'} />
                  </td>
                  <td>{flag.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          <Link href="/dashboard/admin/system">{t('openSystem')}</Link>
        </p>
      </SecSection>
    </main>
  );
}
