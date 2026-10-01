'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import type { CrmAgreementSummary } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';

import {
  amountSortValue,
  displayAmount,
  displayDate,
  initials,
  normalizeStage,
  ownerList,
  paymentLabel,
  projectName,
  unitAddress,
} from './agreements-stage';

const STORAGE_KEY = 'crm.agreements.listColumns.v2';

const DEFAULT_COLUMNS = [
  'musteri',
  'projeDaire',
  'asama',
  'tutar',
  'ortaklik',
  'odemeDurumu',
  'sorumlu',
  'tarih',
  'hemenKira',
] as const;

const OPTIONAL_COLUMNS = [
  'sonrakiEtkinlik',
  'musteriYolculugu',
  'potansiyelDurumu',
  'odemeSekli',
  'hisseOrani',
  'sirketDetaylari',
  'odemeTarihleri',
  'kat',
  'onOdemeTutari',
] as const;

type ColumnId = (typeof DEFAULT_COLUMNS)[number] | (typeof OPTIONAL_COLUMNS)[number];
type SortKey = ColumnId | 'musteri';

function loadColumns(): ColumnId[] {
  if (typeof window === 'undefined') return [...DEFAULT_COLUMNS];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as string[]) : null;
    if (!Array.isArray(parsed) || !parsed.length) return [...DEFAULT_COLUMNS];
    const allowed = new Set<string>([...DEFAULT_COLUMNS, ...OPTIONAL_COLUMNS]);
    const next = parsed.filter((item): item is ColumnId => allowed.has(item));
    return next.length ? next : [...DEFAULT_COLUMNS];
  } catch {
    return [...DEFAULT_COLUMNS];
  }
}

function cellText(row: CrmAgreementSummary, column: ColumnId): string {
  switch (column) {
    case 'musteri':
      return ownerList(row).map((item) => item.display_name).join(' + ');
    case 'projeDaire':
      return [projectName(row), row.project_group === 'reit' ? null : row.unit_number].filter(Boolean).join(' · ');
    case 'asama':
      return normalizeStage(row.stage_label);
    case 'tutar':
      return displayAmount(row) || '';
    case 'ortaklik':
      return row.joint_owners ? 'Ortak' : 'Tek';
    case 'odemeDurumu':
      return paymentLabel(row.payment_status) || '';
    case 'sonrakiEtkinlik':
      return [row.next_activity_title, displayDate(row.next_activity_at)].filter(Boolean).join(' · ');
    case 'sorumlu':
      return row.responsible_name || '';
    case 'tarih':
      return displayDate(row.agreement_date || row.begin_date);
    case 'hemenKira':
      return row.hemen_kira ? 'Evet' : 'Hayır';
    case 'musteriYolculugu':
      return row.customer_journey || '';
    case 'potansiyelDurumu':
      return row.potential_status || '';
    case 'odemeSekli':
      return row.payment_method || '';
    case 'hisseOrani':
      return row.share_ratio || '';
    case 'sirketDetaylari':
      return row.company_details || '';
    case 'odemeTarihleri':
      return row.payment_dates || '';
    case 'kat':
      return row.floor || '';
    case 'onOdemeTutari':
      return row.deposit_amount || '';
    default:
      return '';
  }
}

function sortValue(row: CrmAgreementSummary, column: SortKey): string | number {
  if (column === 'tutar') return amountSortValue(row);
  if (column === 'tarih') return row.agreement_date || row.begin_date || '';
  return cellText(row, column as ColumnId).toLocaleLowerCase('tr');
}

export function AgreementsList({
  items,
  onOpen,
}: {
  items: CrmAgreementSummary[];
  onOpen: (row: CrmAgreementSummary) => void;
}) {
  const t = useTranslations('crm.agreements');
  const { openContact } = useContactCard();
  const [open, setOpen] = useState(false);
  const [columns, setColumns] = useState<ColumnId[]>([...DEFAULT_COLUMNS]);
  const [ready, setReady] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('musteri');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  useEffect(() => {
    setColumns(loadColumns());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready || typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(columns));
  }, [columns, ready]);

  useEffect(() => {
    setPage(1);
  }, [items, pageSize, sortKey, sortDir]);

  const allColumns = useMemo(() => [...DEFAULT_COLUMNS, ...OPTIONAL_COLUMNS], []);

  const sorted = useMemo(() => {
    const next = [...items];
    next.sort((left, right) => {
      const a = sortValue(left, sortKey);
      const b = sortValue(right, sortKey);
      const compared = typeof a === 'number' && typeof b === 'number' ? a - b : String(a).localeCompare(String(b), 'tr');
      return sortDir === 'asc' ? compared : -compared;
    });
    return next;
  }, [items, sortDir, sortKey]);

  const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, pages);
  const start = (safePage - 1) * pageSize;
  const visible = sorted.slice(start, start + pageSize);

  const toggle = (id: ColumnId) => {
    setColumns((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  const toggleSort = (id: ColumnId) => {
    if (sortKey === id) {
      setSortDir((value) => (value === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(id);
    setSortDir('asc');
  };

  return (
    <section className="crm-agreements-list" data-testid="agreements-list">
      <div className="crm-agreements-list-tools">
        <div className="crm-agreements-columns">
          <Button type="button" variant="secondary" size="sm" onClick={() => setOpen((value) => !value)}>
            {t('columnPicker')}
          </Button>
          {open ? (
            <div className="crm-agreements-columns__panel" data-testid="agreements-column-picker">
              {allColumns.map((id) => (
                <label key={id}>
                  <input
                    type="checkbox"
                    checked={columns.includes(id)}
                    disabled={
                      DEFAULT_COLUMNS.includes(id as (typeof DEFAULT_COLUMNS)[number]) &&
                      columns.includes(id) &&
                      columns.filter((item) => DEFAULT_COLUMNS.includes(item as (typeof DEFAULT_COLUMNS)[number])).length <= 3
                    }
                    onChange={() => toggle(id)}
                  />
                  {t(`listColumns.${id}`)}
                </label>
              ))}
            </div>
          ) : null}
        </div>
      </div>
      <div className="crm-agreements-table-wrap">
        <table className="crm-agreements-table" aria-label={t('tableAria')}>
          <thead>
            <tr>
              {columns.map((id) => (
                <th key={id} scope="col" className={`is-${id}`}>
                  <button type="button" onClick={() => toggleSort(id)}>
                    {t(`listColumns.${id}`)}
                    {sortKey === id ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                  </button>
                </th>
              ))}
              <th scope="col" className="is-actions">
                {t('listColumns.actions')}
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => {
              const owners = ownerList(row);
              const amount = displayAmount(row);
              const pay = paymentLabel(row.payment_status);
              const address = unitAddress(row);
              return (
                <tr key={row.id} className="crm-agreements-row" onClick={() => onOpen(row)}>
                  {columns.map((id) => (
                    <td key={`${row.id}:${id}`} className={`is-${id}`}>
                      {id === 'musteri' ? (
                        <div className="crm-agreement-owners">
                          {owners.map((owner) => (
                            <button
                              key={owner.contact_id}
                              type="button"
                              className="crm-agreement-owner-link"
                              title={owner.display_name}
                              onClick={(event) => {
                                event.stopPropagation();
                                openContact(owner.contact_id);
                              }}
                            >
                              {owner.display_name}
                            </button>
                          ))}
                        </div>
                      ) : id === 'projeDaire' ? (
                        <div className="crm-agreement-project" title={[projectName(row), row.unit_number, address].filter(Boolean).join(' · ')}>
                          <strong>{projectName(row)}</strong>
                          {row.project_group !== 'reit' && row.unit_number ? <span>{row.unit_number}</span> : null}
                          {address ? <small>{address}</small> : null}
                          {row.has_unit_change ? <em>{t('unitChangeHint')}</em> : null}
                        </div>
                      ) : id === 'asama' ? (
                        <div className="crm-agreement-stage">
                          <StatusChip tone={normalizeStage(row.stage_label) === 'Kazanıldı' ? 'success' : 'default'}>
                            {normalizeStage(row.stage_label)}
                          </StatusChip>
                          {row.review_required ? <span className="crm-agreements-tag">{t('reviewRequired')}</span> : null}
                        </div>
                      ) : id === 'tutar' ? (
                        <span title={amount || undefined}>{amount || '—'}</span>
                      ) : id === 'odemeDurumu' ? (
                        pay ? (
                          <span className="crm-agreements-pay">
                            <i />
                            {pay}
                          </span>
                        ) : (
                          '—'
                        )
                      ) : id === 'sorumlu' ? (
                        row.responsible_name ? (
                          <span className="crm-agreements-person" title={row.responsible_name}>
                            <em>{initials(row.responsible_name)}</em>
                            {row.responsible_name}
                          </span>
                        ) : (
                          '—'
                        )
                      ) : id === 'hemenKira' ? (
                        <span className={`crm-agreements-rent${row.hemen_kira ? ' is-yes' : ''}`}>
                          {row.hemen_kira ? t('yes') : t('no')}
                        </span>
                      ) : (
                        <span title={cellText(row, id) || undefined}>{cellText(row, id) || '—'}</span>
                      )}
                    </td>
                  ))}
                  <td className="is-actions">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpen(row);
                      }}
                    >
                      {t('openPurchase')}
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <footer className="crm-agreements-pager">
        <p>
          {t('pager', {
            total: sorted.length,
            from: sorted.length ? start + 1 : 0,
            to: Math.min(start + pageSize, sorted.length),
          })}
        </p>
        <div>
          {Array.from({ length: pages }, (_, index) => index + 1).map((item) => (
            <button
              key={item}
              type="button"
              className={item === safePage ? 'is-active' : undefined}
              onClick={() => setPage(item)}
            >
              {item}
            </button>
          ))}
        </div>
        <label>
          {t('pageSize')}
          <select value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))}>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </label>
      </footer>
    </section>
  );
}
