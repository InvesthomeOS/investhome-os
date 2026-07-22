'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  createIncident,
  fetchIncidents,
  fetchSecurityDashboard,
  type SecurityIncident,
} from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';

import { AdminFormModal } from '../../_components/admin-form-modal';
import { SecSection, StatusBadge } from '../../_components/sec-ui';
import { useAdminToast } from '../../_components/use-admin-toast';

export function IncidentsWorkspace() {
  const t = useTranslations('adminSecurity');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { notifySuccess, notifyError } = useAdminToast();
  const [items, setItems] = useState<SecurityIncident[]>([]);
  const [alerts, setAlerts] = useState<Array<{ severity: string; title: string; detail: string }>>([]);
  const [formOpen, setFormOpen] = useState(false);
  const canManage = Boolean(user && hasPermission(user, 'security', 'manage'));

  const load = useCallback(async () => {
    const [inc, dash] = await Promise.all([fetchIncidents(), fetchSecurityDashboard()]);
    setItems(inc.items);
    setAlerts(dash.alerts);
  }, []);

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
    <main className="dashboard" data-sec-workspace="incidents">
      <PageHeader
        eyebrow={t('eyebrow')}
        title={t('incidentsTitle')}
        subtitle={t('incidentsSubtitle')}
        actions={
          canManage ? (
            <Button type="button" onClick={() => setFormOpen(true)}>
              {t('createIncident')}
            </Button>
          ) : null
        }
      />
      <SecSection title={t('securityAlerts')} description={t('securityAlertsHint')}>
        {alerts.length === 0 ? (
          <p className="sec-empty">{t('noAlerts')}</p>
        ) : (
          <ul className="sec-alert-list">
            {alerts.map((a) => (
              <li key={a.title} className={`sec-alert sec-alert--${a.severity}`}>
                <strong>{a.title}</strong>
                <span>{a.detail}</span>
              </li>
            ))}
          </ul>
        )}
      </SecSection>
      <SecSection title={t('incidentList')}>
        {items.length === 0 ? <p className="sec-empty">{t('noIncidents')}</p> : null}
        {items.length > 0 ? (
          <div className="sec-table-wrap">
            <table className="sec-table">
              <thead>
                <tr>
                  <th>{t('colTitle')}</th>
                  <th>{t('colSeverity')}</th>
                  <th>{t('colStatus')}</th>
                  <th>{t('colCreated')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.title}</td>
                    <td>
                      <StatusBadge status={row.severity} />
                    </td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>
                    <td>{new Date(row.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </SecSection>
      <AdminFormModal
        open={formOpen}
        title={t('createIncident')}
        submitLabel={t('createIncident')}
        dirty={false}
        onClose={() => setFormOpen(false)}
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          try {
            await createIncident({
              title: String(form.get('title')),
              severity: String(form.get('severity') || 'medium'),
              summary: String(form.get('summary') || ''),
            });
            setFormOpen(false);
            notifySuccess(t('incidentCreated'));
            await load();
          } catch (err) {
            notifyError(err, t('saveFailed'));
          }
        }}
      >
        <label>
          {t('colTitle')}
          <input name="title" required minLength={3} />
        </label>
        <label>
          {t('colSeverity')}
          <select name="severity" defaultValue="medium">
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="critical">critical</option>
          </select>
        </label>
        <label>
          {t('summary')}
          <textarea name="summary" rows={3} />
        </label>
      </AdminFormModal>
    </main>
  );
}
