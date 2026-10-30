'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import type { CrmAgreementSummary } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';

import {
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
type AgreementSortColumn = 'tarih' | 'hemenKira';

function visiblePages(page: number, pages: number): Array<number | 'ellipsis'> {
  if (pages <= 7) return Array.from({ length: pages }, (_, index) => index + 1);
  const wanted = new Set([1, pages, page - 1, page, page + 1]);
  const nums = [...wanted].filter((value) => value >= 1 && value <= pages).sort((a, b) => a - b);
  const next: Array<number | 'ellipsis'> = [];
  for (const value of nums) {
    const last = next[next.length - 1];
    if (typeof last === 'number' && value - last > 1) next.push('ellipsis');
    next.push(value);
  }
  return next;
}

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

export function AgreementsList({
  items,
  onOpen,
  sortKey,
  sortDir,
  onSort,
  page,
  pages,
  total,
  pageSize,
  onPage,
  onPageSize,
}: {
  items: CrmAgreementSummary[];
  onOpen: (row: CrmAgreementSummary) => void;
  sortKey: 'agreement_date' | 'hemen_kira';
  sortDir: 'asc' | 'desc';
  onSort: (column: AgreementSortColumn) => void;
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPage: (page: number) => void;
  onPageSize: (size: number) => void;
}) {
  const t = useTranslations('crm.agreements');
  const { openContact } = useContactCard();
  const [open, setOpen] = useState(false);
  const [columns, setColumns] = useState<ColumnId[]>([...DEFAULT_COLUMNS]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setColumns(loadColumns());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready || typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(columns));
  }, [columns, ready]);

  const allColumns = useMemo(() => [...DEFAULT_COLUMNS, ...OPTIONAL_COLUMNS], []);
  const from = total ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(page * pageSize, total);

  const toggle = (id: ColumnId) => {
    setColumns((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
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
              {columns.map((id) => {
                const sortable = id === 'tarih' || id === 'hemenKira';
                const active =
                  (id === 'tarih' && sortKey === 'agreement_date') ||
                  (id === 'hemenKira' && sortKey === 'hemen_kira');
                return (
                  <th key={id} scope="col" className={`is-${id}`}>
                    {sortable ? (
                      <button
                        type="button"
                        onClick={() => {
                          if (id === 'tarih' || id === 'hemenKira') onSort(id);
                        }}
                      >
                        {t(`listColumns.${id}`)}
                        {active ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                      </button>
                    ) : (
                      t(`listColumns.${id}`)
                    )}
                  </th>
                );
              })}
              <th scope="col" className="is-actions">
                {t('listColumns.actions')}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => {
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
          {t('pager', { total, from, to })}
        </p>
        <div>
          <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            ‹
          </button>
          {visiblePages(page, pages).map((item, index) =>
            item === 'ellipsis' ? (
              <span key={`ellipsis-${index}`}>…</span>
            ) : (
              <button
                key={item}
                type="button"
                className={item === page ? 'is-active' : undefined}
                onClick={() => onPage(item)}
              >
                {item}
              </button>
            ),
          )}
          <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            ›
          </button>
        </div>
        <label>
          {t('pageSize')}
          <select value={pageSize} onChange={(event) => onPageSize(Number(event.target.value))}>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </label>
      </footer>
    </section>
  );
}
