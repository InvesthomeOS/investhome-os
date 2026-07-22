'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  createApiKey,
  fetchApiKeys,
  revokeApiKey,
  rotateApiKey,
  type ApiKeyItem,
} from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { AdminFormModal } from '../../_components/admin-form-modal';
import { SecSection, StatusBadge } from '../../_components/sec-ui';
import { useAdminToast } from '../../_components/use-admin-toast';

export function ApiKeysWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { notifySuccess, notifyError } = useAdminToast();
  const [items, setItems] = useState<ApiKeyItem[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [revealedSecret, setRevealedSecret] = useState<string | null>(null);
  const canManage = Boolean(user && hasPermission(user, 'security', 'manage'));

  const load = useCallback(async () => {
    try {
      const res = await fetchApiKeys();
      setItems(res.items);
    } catch (err) {
      notifyError(err, t('loadError'));
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
    <main className="dashboard" data-sec-workspace="api-keys">
      <PageHeader
        eyebrow={t('eyebrow')}
        title={t('apiKeysTitle')}
        subtitle={t('apiKeysSubtitle')}
        actions={
          canManage ? (
            <Button type="button" onClick={() => setFormOpen(true)}>
              {t('issueKey')}
            </Button>
          ) : null
        }
      />
      {revealedSecret ? (
        <div className="sec-secret-once" role="status">
          <strong>{t('secretOnce')}</strong>
          <code>{revealedSecret}</code>
          <Button type="button" variant="ghost" onClick={() => setRevealedSecret(null)}>
            {t('dismissSecret')}
          </Button>
        </div>
      ) : null}
      <SecSection title={t('apiKeysList')}>
        {items.length === 0 ? <p className="sec-empty">{t('noApiKeys')}</p> : null}
        {items.length > 0 ? (
          <div className="sec-table-wrap">
            <table className="sec-table">
              <thead>
                <tr>
                  <th>{t('colName')}</th>
                  <th>{t('colPrefix')}</th>
                  <th>{t('colScopes')}</th>
                  <th>{t('colStatus')}</th>
                  <th>{t('colExpires')}</th>
                  <th>{t('colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.name}</td>
                    <td>
                      <code>{row.key_prefix}…</code>
                    </td>
                    <td>{row.scopes.join(', ') || '—'}</td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>
                    <td>{row.expires_at ? new Date(row.expires_at).toLocaleDateString() : '—'}</td>
                    <td>
                      {canManage && row.status === 'active' ? (
                        <>
                          <Button
                            type="button"
                            variant="ghost"
                            onClick={async () => {
                              try {
                                const res = await rotateApiKey(row.id);
                                setRevealedSecret(res.secret);
                                notifySuccess(t('keyRotated'));
                                await load();
                              } catch (err) {
                                notifyError(err, t('saveFailed'));
                              }
                            }}
                          >
                            {t('rotate')}
                          </Button>
                          <Button
                            type="button"
                            variant="danger"
                            onClick={async () => {
                              try {
                                await revokeApiKey(row.id);
                                notifySuccess(t('keyRevoked'));
                                await load();
                              } catch (err) {
                                notifyError(err, t('saveFailed'));
                              }
                            }}
                          >
                            {t('revoke')}
                          </Button>
                        </>
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
      <AdminFormModal
        open={formOpen}
        title={t('issueKey')}
        submitLabel={t('issueKey')}
        dirty={false}
        onClose={() => setFormOpen(false)}
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          try {
            const res = await createApiKey({
              name: String(form.get('name')),
              scopes: String(form.get('scopes') || '')
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
            });
            setRevealedSecret(res.secret);
            setFormOpen(false);
            notifySuccess(t('keyIssued'));
            await load();
          } catch (err) {
            notifyError(err, t('saveFailed'));
          }
        }}
      >
        <label>
          {t('colName')}
          <input name="name" required minLength={2} />
        </label>
        <label>
          {t('colScopes')}
          <input name="scopes" placeholder="read, write" />
        </label>
      </AdminFormModal>
    </main>
  );
}
