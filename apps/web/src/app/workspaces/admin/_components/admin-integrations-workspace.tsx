'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, Input, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import type {
  AdminIntegrationStatus,
  AdminIntegrationsPreview,
} from '../admin-subpages-model';

const STATUS_TONE: Record<
  AdminIntegrationStatus,
  'success' | 'warning' | 'info' | 'default' | 'danger'
> = {
  connected: 'success',
  degraded: 'warning',
  disconnected: 'danger',
};

export function AdminIntegrationsWorkspace({ preview }: { preview: AdminIntegrationsPreview }) {
  const t = useTranslations('crm.admin.integrationsPage');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [rows, setRows] = useState(preview.rows);
  const [toast, setToast] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return rows.filter((row) => {
      if (status && row.status !== status) return false;
      if (search) {
        const q = search.trim().toLowerCase();
        if (!row.name.toLowerCase().includes(q) && !row.provider.toLowerCase().includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [rows, search, status]);

  const toggle = (id: string) => {
    setRows((prev) =>
      prev.map((row) => {
        if (row.id !== id) return row;
        const nextStatus: AdminIntegrationStatus =
          row.status === 'connected' ? 'disconnected' : 'connected';
        return {
          ...row,
          status: nextStatus,
          lastSync: nextStatus === 'connected' ? t('justNow') : t('never'),
        };
      }),
    );
    setToast(t('toast.updated'));
    window.setTimeout(() => setToast(null), 2200);
  };

  return (
    <div className="admin-ws admin-subpage" data-testid="admin-integrations">
      {toast ? (
        <div className="admin-subpage__toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}

      <header className="admin-ws__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="admin-subpage__toolbar" aria-label={t('filters.aria')}>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('filters.searchPlaceholder')}
          aria-label={t('filters.search')}
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          aria-label={t('filters.status')}
        >
          <option value="">{t('filters.anyStatus')}</option>
          {(['connected', 'degraded', 'disconnected'] as AdminIntegrationStatus[]).map((key) => (
            <option key={key} value={key}>
              {t(`status.${key}`)}
            </option>
          ))}
        </Select>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            setSearch('');
            setStatus('');
          }}
        >
          {t('filters.clear')}
        </Button>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : (
        <ul className="admin-subpage__cards" aria-label={t('listAria')}>
          {filtered.map((row) => (
            <li key={row.id} className="admin-subpage__card">
              <span className="admin-subpage__card-icon" aria-hidden="true">
                <IhIcon name={row.icon} size={16} />
              </span>
              <div className="admin-subpage__card-copy">
                <strong>{row.name}</strong>
                <span>
                  {row.provider} · {t('lastSync')}: {row.lastSync}
                </span>
              </div>
              <StatusChip tone={STATUS_TONE[row.status]}>{t(`status.${row.status}`)}</StatusChip>
              <Button type="button" variant="secondary" size="sm" onClick={() => toggle(row.id)}>
                {row.status === 'connected' ? t('disconnect') : t('connect')}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
