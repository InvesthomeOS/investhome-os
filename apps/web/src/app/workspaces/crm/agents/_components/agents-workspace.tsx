'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { SegmentedControl, StatusChip } from '@investhome/ui';

import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { ContactListParams } from '@/workspaces/crm/api/contacts';
import type { CrmContactStatus } from '@/workspaces/crm/types';

import '../../contacts/_components/ds/contacts-ds.css';

type AgentStatusFilter = 'all' | 'active' | 'inactive';

export function AgentsWorkspace() {
  const t = useTranslations('crm.agents');
  const tTypes = useTranslations('crm.contactTypes');
  const tStatus = useTranslations('crm.statuses');
  const { openContact } = useContactCard();
  const [status, setStatus] = useState<AgentStatusFilter>('active');

  const listParams: ContactListParams = useMemo(
    () => ({
      contact_types: ['broker', 'realtor'],
      status: status === 'all' ? undefined : (status as CrmContactStatus),
      page: 1,
      page_size: 50,
      sort_by: 'display_name',
      sort_dir: 'asc',
    }),
    [status],
  );

  const query = useQuery(contactQueries.list(listParams));
  const items = query.data?.items ?? [];

  return (
    <div className="ctc-ds" data-testid="crm-agents-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="ctc-ds__toolbar" aria-label={t('statusFilter')}>
        <SegmentedControl
          ariaLabel={t('statusFilter')}
          value={status}
          onChange={setStatus}
          options={[
            { value: 'all', label: t('statusAll') },
            { value: 'active', label: t('statusActive') },
            { value: 'inactive', label: t('statusPassive') },
          ]}
        />
      </section>

      {query.isLoading ? <p>{t('loading')}</p> : null}
      {query.isError ? <p>{t('loadError')}</p> : null}

      {!query.isLoading && !query.isError ? (
        <section className="ctc-ds__table-section" aria-label={t('tableAria')}>
          {items.length === 0 ? (
            <div className="ctc-ds__empty" data-testid="crm-agents-empty">
              <strong>{t('emptyTitle')}</strong>
              <p>{t('emptyDescription')}</p>
            </div>
          ) : (
            <div className="ctc-ds__table-wrap">
              <table className="ctc-ds__table">
                <thead>
                  <tr>
                    <th scope="col">{t('columns.name')}</th>
                    <th scope="col">{t('columns.type')}</th>
                    <th scope="col">{t('columns.company')}</th>
                    <th scope="col">{t('columns.phone')}</th>
                    <th scope="col">{t('columns.email')}</th>
                    <th scope="col">{t('columns.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((agent) => (
                    <tr key={agent.id} className="ctc-ds__row" onClick={() => openContact(agent.id)}>
                      <td>
                        <strong>{agent.display_name}</strong>
                      </td>
                      <td>
                        {(agent.contact_types?.length ? agent.contact_types : [agent.contact_type])
                          .map((type) => tTypes(type))
                          .join(', ')}
                      </td>
                      <td>{agent.organization_name ?? agent.company_name ?? '—'}</td>
                      <td>
                        {agent.primary_phone ?? '—'}
                        {agent.secondary_phones?.length ? ` · ${agent.secondary_phones[0]}` : ''}
                      </td>
                      <td>{agent.primary_email ?? '—'}</td>
                      <td>
                        <StatusChip tone={agent.status === 'active' ? 'success' : 'default'}>
                          {agent.review_required ? 'İnceleme Gerekli' : tStatus(agent.status)}
                        </StatusChip>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
