'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  fetchSessions,
  terminateAllSessions,
  terminateSession,
  type AuthSessionItem,
} from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { SecSection, StatusBadge } from '../../_components/sec-ui';
import { useAdminToast } from '../../_components/use-admin-toast';

export function SessionsWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { notifySuccess, notifyError } = useAdminToast();
  const [items, setItems] = useState<AuthSessionItem[]>([]);
  const [loading, setLoading] = useState(true);

  const canManage = Boolean(user && hasPermission(user, 'security', 'manage'));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchSessions();
      setItems(res.items);
    } catch (err) {
      notifyError(err, t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [notifyError, t]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (!hasPermission(user, 'security', 'view')) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [authLoading, load, router, user]);

  return (
    <main className="dashboard" data-sec-workspace="sessions">
      <PageHeader
        eyebrow={t('eyebrow')}
        title={t('sessionsTitle')}
        subtitle={t('sessionsSubtitle')}
        actions={
          canManage ? (
            <Button
              type="button"
              variant="danger"
              onClick={async () => {
                try {
                  const res = await terminateAllSessions();
                  notifySuccess(t('sessionsTerminated', { count: res.sessions_revoked }));
                  await load();
                } catch (err) {
                  notifyError(err, t('saveFailed'));
                }
              }}
            >
              {t('terminateAll')}
            </Button>
          ) : null
        }
      />
      <SecSection title={t('activeSessions')}>
        {loading ? <p>{t('loading')}</p> : null}
        {!loading && items.length === 0 ? <p className="sec-empty">{t('noSessions')}</p> : null}
        {items.length > 0 ? (
          <div className="sec-table-wrap">
            <table className="sec-table">
              <thead>
                <tr>
                  <th>{t('colUser')}</th>
                  <th>{t('colDevice')}</th>
                  <th>{t('colIp')}</th>
                  <th>{t('colLastSeen')}</th>
                  <th>{t('colStatus')}</th>
                  <th>{t('colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id}>
                    <td>
                      {row.user_name ?? row.user_email ?? row.user_id}
                      {row.is_current ? ` (${t('currentSession')})` : ''}
                    </td>
                    <td>{row.device_label ?? '—'}</td>
                    <td>{row.ip_address ?? '—'}</td>
                    <td>{new Date(row.last_seen_at).toLocaleString()}</td>
                    <td>
                      <StatusBadge status={row.revoked_at ? 'revoked' : 'active'} />
                    </td>
                    <td>
                      {canManage && !row.revoked_at ? (
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={async () => {
                            try {
                              await terminateSession(row.id);
                              notifySuccess(t('sessionTerminated'));
                              await load();
                            } catch (err) {
                              notifyError(err, t('saveFailed'));
                            }
                          }}
                        >
                          {t('terminate')}
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
        ) : null}
      </SecSection>
    </main>
  );
}
