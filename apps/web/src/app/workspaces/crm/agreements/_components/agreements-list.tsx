'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import type { CrmAgreementSummary } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';

import { displayDate, unitLine } from './agreements-stage';

const STORAGE_KEY = 'crm.agreements.listColumns.v1';

const DEFAULT_COLUMNS = [
  'musteri',
  'projeDaire',
  'asama',
  'tutar',
  'ortaklik',
  'odemeDurumu',
  'sonrakiEtkinlik',
  'sorumlu',
  'tarih',
  'hemenKira',
] as const;

const OPTIONAL_COLUMNS = [
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

function cell(row: CrmAgreementSummary, column: ColumnId): string {
  switch (column) {
    case 'musteri':
      return row.owners_label || row.contact_name || '';
    case 'projeDaire':
      return unitLine(row);
    case 'asama':
      return row.stage_label || row.status;
    case 'tutar':
      return row.amount_label || row.investment_amount || '';
    case 'ortaklik':
      return row.joint_owners ? 'Ortak' : 'Tek';
    case 'odemeDurumu':
      return row.payment_status || '';
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
}: {
  items: CrmAgreementSummary[];
  onOpen: (row: CrmAgreementSummary) => void;
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

  const toggle = (id: ColumnId) => {
    setColumns((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  return (
    <section className="ctc-ds__table-section" data-testid="agreements-list">
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
                    disabled={DEFAULT_COLUMNS.includes(id as (typeof DEFAULT_COLUMNS)[number]) && columns.includes(id) && columns.filter((item) => DEFAULT_COLUMNS.includes(item as (typeof DEFAULT_COLUMNS)[number])).length <= 3}
                    onChange={() => toggle(id)}
                  />
                  {t(`listColumns.${id}`)}
                </label>
              ))}
            </div>
          ) : null}
        </div>
      </div>
      <div className="ctc-ds__table-wrap">
        <table className="ctc-ds__table crm-agreements-table" aria-label={t('tableAria')}>
          <thead>
            <tr>
              {columns.map((id) => (
                <th key={id} scope="col">
                  {t(`listColumns.${id}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} className="ctc-ds__row" onClick={() => onOpen(row)}>
                {columns.map((id) => (
                  <td key={`${row.id}:${id}`}>
                    {id === 'musteri' ? (
                      <div className="crm-agreement-owners">
                        {(row.participants?.length
                          ? row.participants
                          : [{ contact_id: row.contact_id, display_name: row.contact_name ?? row.contact_id }]
                        ).map((owner) => (
                          <button
                            key={owner.contact_id}
                            type="button"
                            className="crm-agreement-owner-link"
                            onClick={(event) => {
                              event.stopPropagation();
                              openContact(owner.contact_id);
                            }}
                          >
                            {owner.display_name}
                          </button>
                        ))}
                      </div>
                    ) : id === 'asama' ? (
                      <StatusChip tone={row.status === 'active' ? 'success' : 'default'}>
                        {row.review_required ? t('reviewRequired') : cell(row, id) || '—'}
                      </StatusChip>
                    ) : (
                      cell(row, id)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
