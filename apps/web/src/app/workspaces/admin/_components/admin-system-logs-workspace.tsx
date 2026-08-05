'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, Input, Select, StatusChip } from '@investhome/ui';

import type { SystemLogLevel, SystemLogsPreview } from '../admin-subpages-model';

const LEVEL_TONE: Record<SystemLogLevel, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  info: 'info',
  warning: 'warning',
  error: 'danger',
  debug: 'default',
};

export function AdminSystemLogsWorkspace({ preview }: { preview: SystemLogsPreview }) {
  const t = useTranslations('crm.admin.systemLogs');
  const [search, setSearch] = useState('');
  const [level, setLevel] = useState('');
  const [service, setService] = useState('');

  const filtered = useMemo(() => {
    return preview.rows.filter((row) => {
      if (level && row.level !== level) return false;
      if (service && row.service !== service) return false;
      if (search) {
        const q = search.trim().toLowerCase();
        if (
          !row.message.toLowerCase().includes(q) &&
          !row.actor.toLowerCase().includes(q) &&
          !row.service.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [preview.rows, search, level, service]);

  const services = useMemo(
    () => Array.from(new Set(preview.rows.map((r) => r.service))).sort(),
    [preview.rows],
  );

  return (
    <div className="admin-ws admin-subpage" data-testid="admin-system-logs">
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
        <Select value={level} onChange={(e) => setLevel(e.target.value)} aria-label={t('filters.level')}>
          <option value="">{t('filters.anyLevel')}</option>
          {(['info', 'warning', 'error', 'debug'] as SystemLogLevel[]).map((key) => (
            <option key={key} value={key}>
              {t(`levels.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          value={service}
          onChange={(e) => setService(e.target.value)}
          aria-label={t('filters.service')}
        >
          <option value="">{t('filters.anyService')}</option>
          {services.map((key) => (
            <option key={key} value={key}>
              {key}
            </option>
          ))}
        </Select>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            setSearch('');
            setLevel('');
            setService('');
          }}
        >
          {t('filters.clear')}
        </Button>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : (
        <div className="admin-subpage__table-wrap">
          <table className="admin-subpage__table">
            <thead>
              <tr>
                <th>{t('columns.timestamp')}</th>
                <th>{t('columns.level')}</th>
                <th>{t('columns.service')}</th>
                <th>{t('columns.message')}</th>
                <th>{t('columns.actor')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id}>
                  <td>{row.timestamp}</td>
                  <td>
                    <StatusChip tone={LEVEL_TONE[row.level]}>{t(`levels.${row.level}`)}</StatusChip>
                  </td>
                  <td>{row.service}</td>
                  <td>{row.message}</td>
                  <td>{row.actor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
