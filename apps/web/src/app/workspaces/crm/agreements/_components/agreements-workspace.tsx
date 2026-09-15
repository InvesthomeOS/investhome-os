'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Select, StatusChip } from '@investhome/ui';

import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';

import '../../contacts/_components/ds/contacts-ds.css';

const FALLBACK_GROUPS = [
  { id: '1307_k_st', label: '1307 K St' },
  { id: '1313_penn', label: '1313 Penn' },
  { id: '1812_h_pl', label: '1812 H Pl' },
  { id: '2319_ontario', label: '2319 Ontario' },
  { id: 'reit', label: 'REIT' },
  { id: 'the_temple', label: 'The Temple' },
  { id: 'uniloft', label: 'Uniloft' },
];

export function AgreementsWorkspace() {
  const t = useTranslations('crm.agreements');
  const { openContact } = useContactCard();
  const [projectGroup, setProjectGroup] = useState('');

  const query = useQuery({
    queryKey: ['crm', 'agreements', projectGroup],
    queryFn: () =>
      fetchAgreements({
        project_group: projectGroup || undefined,
        page: 1,
        page_size: 100,
      }),
  });

  const groups = query.data?.project_groups?.length ? query.data.project_groups : FALLBACK_GROUPS;
  const items = query.data?.items ?? [];

  const grouped = useMemo(() => {
    const map = new Map<string, typeof items>();
    for (const row of items) {
      const key = row.project_group_label || row.project_group;
      const list = map.get(key) ?? [];
      list.push(row);
      map.set(key, list);
    }
    return [...map.entries()];
  }, [items]);

  return (
    <div className="ctc-ds" data-testid="crm-agreements-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="ctc-ds__toolbar" aria-label={t('projectFilter')}>
        <Select
          label={t('projectFilter')}
          value={projectGroup}
          onChange={(event) => setProjectGroup(event.target.value)}
        >
          <option value="">{t('allProjects')}</option>
          {groups.map((group) => (
            <option key={group.id} value={group.id}>
              {group.label}
            </option>
          ))}
        </Select>
      </section>

      {query.isLoading ? <p>{t('loading')}</p> : null}
      {query.isError ? <p>{t('loadError')}</p> : null}

      {!query.isLoading && !query.isError ? (
        <section className="ctc-ds__table-section" aria-label={t('tableAria')}>
          {items.length === 0 ? (
            <div className="ctc-ds__empty" data-testid="crm-agreements-empty">
              <strong>{t('emptyTitle')}</strong>
              <p>{t('emptyDescription')}</p>
            </div>
          ) : (
            grouped.map(([groupLabel, rows]) => {
              const isReit = rows.some((row) => row.project_group === 'reit') || groupLabel === 'REIT';
              return (
              <div key={groupLabel} className="ctc-ds__table-wrap">
                <h2>{groupLabel}</h2>
                <table className="ctc-ds__table">
                  <thead>
                    <tr>
                      <th scope="col">{t('columns.contact')}</th>
                      <th scope="col">{t('columns.project')}</th>
                      <th scope="col">{isReit ? t('columns.investmentAmount') : t('columns.unit')}</th>
                      <th scope="col">{t('columns.email')}</th>
                      <th scope="col">{t('columns.phone')}</th>
                      <th scope="col">{t('columns.status')}</th>
                      <th scope="col">{t('columns.date')}</th>
                      <th scope="col">{t('columns.source')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr
                        key={row.id}
                        className="ctc-ds__row"
                        onClick={() => openContact(row.contact_id)}
                      >
                        <td>
                          <strong>{row.contact_name ?? row.contact_id}</strong>
                        </td>
                        <td>{row.project_group_label}</td>
                        <td>
                          {isReit ? (row.investment_amount ?? '') : (row.unit_number ?? '')}
                        </td>
                        <td>{row.contact_email ?? ''}</td>
                        <td>{row.contact_phone ?? ''}</td>
                        <td>
                          <StatusChip tone={row.status === 'active' ? 'success' : 'default'}>
                            {row.review_required ? t('reviewRequired') : row.status}
                          </StatusChip>
                        </td>
                        <td>{row.agreement_date ?? ''}</td>
                        <td>{row.source_external_id ?? row.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              );
            })
          )}
        </section>
      ) : null}
    </div>
  );
}
