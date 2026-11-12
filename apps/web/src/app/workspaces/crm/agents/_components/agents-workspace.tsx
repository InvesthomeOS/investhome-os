'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button } from '@investhome/ui';

import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { CrmRecordDialog, type CrmRecordMode } from '@/workspaces/crm/crm-record-dialog';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchActivities } from '@/workspaces/crm/api/activities';
import { archiveAgent, restoreAgent } from '@/workspaces/crm/api/contacts';
import { convertCrmLead } from '@/workspaces/crm/api/crm-leads';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { ContactListParams } from '@/workspaces/crm/api/contacts';
import type { CrmActivitySummary } from '@/workspaces/crm/types/activities';
import type { CrmContactSummary } from '@/workspaces/crm/types';

import { AgentsActivities } from './agents-activities';
import { AgentsCalendar } from './agents-calendar';
import { AgentsKanban } from './agents-kanban';
import { AgentsList } from './agents-list';
import { buildActivityIndex } from './agents-stage';

import '../../contacts/_components/ds/contacts-ds.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import '../../agreements/_components/agreements-workspace.css';

const VIEW_TABS = [
  { id: 'kanban', labelKey: 'views.kanban' },
  { id: 'list', labelKey: 'views.list' },
  { id: 'activities', labelKey: 'views.activities' },
  { id: 'calendar', labelKey: 'views.calendar' },
] as const;

type ViewId = (typeof VIEW_TABS)[number]['id'];
type SectionId = 'agents' | 'customers';

const AGENT_PARAMS: ContactListParams = {
  category: 'agent',
  page: 1,
  page_size: 100,
  sort_by: 'display_name',
  sort_dir: 'asc',
};

const CUSTOMER_PARAMS: ContactListParams = {
  bitrix_list: 'agency_customers',
  page: 1,
  page_size: 100,
  sort_by: 'display_name',
  sort_dir: 'asc',
};

async function fetchAgentActivities(ids: string[]): Promise<CrmActivitySummary[]> {
  if (!ids.length) return [];
  const pages = await Promise.allSettled(
    ids.map((id) =>
      fetchActivities({
        entity_type: 'contact',
        entity_id: id,
        page: 1,
        page_size: 50,
        sort_by: 'created_at',
        sort_dir: 'desc',
      }),
    ),
  );
  return pages.flatMap((page) => (page.status === 'fulfilled' ? page.value.items : []));
}

export function AgentsWorkspace() {
  const t = useTranslations('crm.agents');
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const { openContact } = useContactCard();
  const { has, user } = useCrmAccess();
  const queryClient = useQueryClient();

  const [section, setSection] = useState<SectionId>('agents');
  const [view, setView] = useState<ViewId>('kanban');
  const [createMode, setCreateMode] = useState<CrmRecordMode | null>(null);

  const canUpdate = canUpdateCrm(user);
  const canCreate = has('create');

  const copy =
    locale === 'tr'
      ? {
          agents: 'Acenteler',
          customers: 'Acente Müşterileri',
          customersSubtitle: 'Acenteler tarafından takip edilen müşteriler.',
          customer: 'Müşteri',
          phone: 'Telefon',
          email: 'E-posta',
          responsible: 'Sorumlu',
          lastContact: 'Son İletişim',
          action: 'İşlem',
          closeSale: 'Satış Kapamaya Taşı',
          converting: 'Taşınıyor…',
          customerCount: (count: number) => `${count} müşteri`,
          noCustomers: 'Acente müşterisi bulunamadı.',
          confirmSale: (name: string) =>
            `${name} Satış Kapama aşamasına taşınacak. Devam edilsin mi?`,
        }
      : {
          agents: 'Agents',
          customers: 'Agency Customers',
          customersSubtitle: 'Customers managed by agencies.',
          customer: 'Customer',
          phone: 'Phone',
          email: 'Email',
          responsible: 'Owner',
          lastContact: 'Last Contact',
          action: 'Action',
          closeSale: 'Move to Sales Closing',
          converting: 'Moving…',
          customerCount: (count: number) => `${count} customers`,
          noCustomers: 'No agency customers found.',
          confirmSale: (name: string) =>
            `Move ${name} to Sales Closing?`,
        };

  const refreshAgents = () => {
    void queryClient.invalidateQueries({ queryKey: ['crm', 'contacts'] });
  };

  const archiveMutation = useMutation({
    mutationFn: (id: string) => archiveAgent(id),
    onSuccess: refreshAgents,
  });

  const restoreMutation = useMutation({
    mutationFn: (id: string) => restoreAgent(id),
    onSuccess: refreshAgents,
  });

  const convertMutation = useMutation({
    mutationFn: ({ leadId, personId }: { leadId: string; personId: string }) =>
      convertCrmLead(leadId, personId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['crm'] });
    },
  });

  const agentsQuery = useQuery(contactQueries.list(AGENT_PARAMS));
  const customersQuery = useQuery(contactQueries.list(CUSTOMER_PARAMS));

  const items = useMemo(
    () => agentsQuery.data?.items ?? [],
    [agentsQuery.data?.items],
  );

  const customers = useMemo(
    () => customersQuery.data?.items ?? [],
    [customersQuery.data?.items],
  );

  const agentIds = useMemo(() => items.map((item) => item.id), [items]);

  const activityQuery = useQuery({
    queryKey: ['crm', 'agents', 'activities', agentIds],
    queryFn: () => fetchAgentActivities(agentIds),
    enabled: section === 'agents' && agentIds.length > 0,
  });

  const activity = useMemo(
    () => buildActivityIndex(agentIds, activityQuery.data ?? []),
    [agentIds, activityQuery.data],
  );

  const openAgent = (agent: CrmContactSummary | string) => {
    openContact(typeof agent === 'string' ? agent : agent.id);
  };

  return (
    <div className="ctc-ds crm-agents-workspace" data-testid="crm-agents-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{section === 'agents' ? copy.agents : copy.customers}</h1>
          <p>{section === 'agents' ? t('subtitle') : copy.customersSubtitle}</p>
        </div>

        <div className="crm-agreements-views" role="tablist" aria-label="Acenteler">
          {canCreate ? (
            <Button
              type="button"
              size="sm"
              onClick={() => setCreateMode(section === 'agents' ? 'agent' : 'agency-customer')}
            >
              {section === 'agents' ? 'Yeni Acente' : 'Yeni Acente Müşterisi'}
            </Button>
          ) : null}
          <button
            type="button"
            role="tab"
            aria-selected={section === 'agents'}
            className={section === 'agents' ? 'is-active' : undefined}
            onClick={() => setSection('agents')}
          >
            {copy.agents}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={section === 'customers'}
            className={section === 'customers' ? 'is-active' : undefined}
            onClick={() => setSection('customers')}
          >
            {copy.customers}
          </button>
        </div>
      </header>

      {section === 'agents' ? (
        <>
          <section className="ctc-ds__toolbar crm-agreements-toolbar">
            <p className="crm-agreements-count" data-testid="agents-count">
              {agentsQuery.data
                ? t('count', { count: agentsQuery.data.total })
                : t('loading')}
            </p>

            <div className="crm-agreements-views" role="tablist" aria-label={t('viewsLabel')}>
              {VIEW_TABS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={view === item.id}
                  className={view === item.id ? 'is-active' : undefined}
                  data-testid={`agents-view-${item.id}`}
                  onClick={() => setView(item.id)}
                >
                  {t(item.labelKey)}
                </button>
              ))}
            </div>
          </section>

          {agentsQuery.isLoading ? <p>{t('loading')}</p> : null}
          {agentsQuery.isError ? <p>{t('loadError')}</p> : null}

          {!agentsQuery.isLoading && !agentsQuery.isError && items.length === 0 ? (
            <div className="ctc-ds__empty" data-testid="crm-agents-empty">
              <strong>{t('emptyTitle')}</strong>
              <p>{t('emptyDescription')}</p>
            </div>
          ) : null}

          {!agentsQuery.isLoading &&
          !agentsQuery.isError &&
          items.length > 0 &&
          view === 'kanban' ? (
            <AgentsKanban items={items} activity={activity} onOpen={openAgent} />
          ) : null}

          {!agentsQuery.isLoading &&
          !agentsQuery.isError &&
          items.length > 0 &&
          view === 'list' ? (
            <AgentsList
              items={items}
              activity={activity}
              onOpen={openAgent}
              canArchive={has('archive')}
              canRestore={has('restore')}
              onArchive={(agent) => archiveMutation.mutate(agent.id)}
              onRestore={(agent) => restoreMutation.mutate(agent.id)}
            />
          ) : null}

          {!agentsQuery.isLoading && !agentsQuery.isError && view === 'activities' ? (
            activityQuery.isLoading ? (
              <p>{t('loading')}</p>
            ) : (
              <AgentsActivities
                items={items}
                activities={activity.items}
                onOpen={openAgent}
              />
            )
          ) : null}

          {!agentsQuery.isLoading && !agentsQuery.isError && view === 'calendar' ? (
            activityQuery.isLoading ? (
              <p>{t('loading')}</p>
            ) : (
              <AgentsCalendar
                items={items}
                activities={activity.items}
                onOpen={openAgent}
              />
            )
          ) : null}
        </>
      ) : (
        <>
          <section className="ctc-ds__toolbar crm-agreements-toolbar">
            <p className="crm-agreements-count">
              {customersQuery.data
                ? copy.customerCount(customersQuery.data.total)
                : t('loading')}
            </p>
          </section>

          {customersQuery.isLoading ? <p>{t('loading')}</p> : null}
          {customersQuery.isError ? <p>{t('loadError')}</p> : null}

          {!customersQuery.isLoading &&
          !customersQuery.isError &&
          customers.length === 0 ? (
            <div className="ctc-ds__empty">
              <strong>{copy.noCustomers}</strong>
            </div>
          ) : null}

          {!customersQuery.isLoading &&
          !customersQuery.isError &&
          customers.length > 0 ? (
            <section className="ctc-ds__table-section">
              <div className="ctc-ds__table-wrap">
                <table className="ctc-ds__table crm-agreements-table">
                  <thead>
                    <tr>
                      <th>{copy.customer}</th>
                      <th>{copy.phone}</th>
                      <th>{copy.email}</th>
                      <th>{copy.responsible}</th>
                      <th>{copy.lastContact}</th>
                      <th>{copy.action}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customers.map((customer) => (
                      <tr
                        key={customer.id}
                        className="ctc-ds__row"
                        onClick={() => openContact(customer.id)}
                      >
                        <td>{customer.display_name}</td>
                        <td>{customer.primary_phone || '—'}</td>
                        <td>{customer.primary_email || '—'}</td>
                        <td>{customer.owner_name || customer.bitrix_responsible || '—'}</td>
                        <td>
                          {customer.last_contact_at
                            ? new Date(customer.last_contact_at).toLocaleDateString(locale)
                            : '—'}
                        </td>
                        <td>
                          {canUpdate && customer.lead_id ? (
                            <Button
                              type="button"
                              size="sm"
                              variant="secondary"
                              disabled={convertMutation.isPending}
                              onClick={(event) => {
                                event.stopPropagation();
                                if (!window.confirm(copy.confirmSale(customer.display_name))) return;
                                convertMutation.mutate({
                                  leadId: customer.lead_id as string,
                                  personId: customer.id,
                                });
                              }}
                            >
                              {convertMutation.isPending
                                ? copy.converting
                                : copy.closeSale}
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
            </section>
          ) : null}
        </>
      )}
      {createMode ? (
        <CrmRecordDialog
          mode={createMode}
          onClose={() => setCreateMode(null)}
          onDone={() => {
            setCreateMode(null);
            refreshAgents();
          }}
        />
      ) : null}
    </div>
  );
}
