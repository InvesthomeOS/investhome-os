'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Select } from '@investhome/ui';

import { fetchAgreements, type CrmAgreementSummary } from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';

import { AgreementsActivities } from './agreements-activities';
import { AgreementsCalendar } from './agreements-calendar';
import { AgreementsKanban } from './agreements-kanban';
import { AgreementsList } from './agreements-list';
import { PROJECT_SELECTOR } from './agreements-stage';

import '../../contacts/_components/ds/contacts-ds.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import './agreements-workspace.css';

const VIEWS = [
  { id: 'kanban', labelKey: 'views.kanban' },
  { id: 'list', labelKey: 'views.list' },
  { id: 'activities', labelKey: 'views.activities' },
  { id: 'calendar', labelKey: 'views.calendar' },
] as const;

type ViewId = (typeof VIEWS)[number]['id'];

export function AgreementsWorkspace() {
  const t = useTranslations('crm.agreements');
  const router = useRouter();
  const searchParams = useSearchParams();
  const [projectGroup, setProjectGroup] = useState(searchParams.get('project') || '');
  const [view, setView] = useState<ViewId>('kanban');

  const query = useQuery({
    queryKey: ['crm', 'agreements', projectGroup],
    queryFn: () =>
      fetchAgreements({
        project_group: projectGroup || undefined,
        page: 1,
        page_size: 200,
      }),
  });

  const items = query.data?.items ?? [];
  const groups = useMemo(() => {
    const api = query.data?.project_groups ?? [];
    return PROJECT_SELECTOR.map((item) => ({
      id: item.id,
      label: item.label,
      apiLabel: api.find((group) => group.id === item.id)?.label || item.label,
    }));
  }, [query.data?.project_groups]);

  const openPurchase = (row: CrmAgreementSummary) => {
    router.push(salesDetailUrl(row.contact_id, row.id));
  };

  const openAgreement = (agreementId: string, contactId: string) => {
    router.push(salesDetailUrl(contactId, agreementId));
  };

  return (
    <div className="ctc-ds" data-testid="crm-agreements-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-agreements-views" role="tablist" aria-label={t('viewsLabel')}>
          {VIEWS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              className={view === item.id ? 'is-active' : undefined}
              data-testid={`agreements-view-${item.id}`}
              onClick={() => setView(item.id)}
            >
              {t(item.labelKey)}
            </button>
          ))}
        </div>
      </header>

      <section className="ctc-ds__toolbar crm-agreements-toolbar" aria-label={t('projectFilter')}>
        <Select
          label={t('projectFilter')}
          value={projectGroup}
          data-testid="agreements-project-filter"
          onChange={(event) => setProjectGroup(event.target.value)}
        >
          <option value="">{t('allProjects')}</option>
          {groups.map((group) => (
            <option key={group.id} value={group.id}>
              {group.label}
            </option>
          ))}
        </Select>
        <p className="crm-agreements-count" data-testid="agreements-count">
          {query.data ? t('count', { count: query.data.total }) : t('loading')}
        </p>
      </section>

      {query.isLoading ? <p>{t('loading')}</p> : null}
      {query.isError ? <p>{t('loadError')}</p> : null}

      {!query.isLoading && !query.isError && items.length === 0 ? (
        <div className="ctc-ds__empty" data-testid="crm-agreements-empty">
          <strong>{t('emptyTitle')}</strong>
          <p>{t('emptyDescription')}</p>
        </div>
      ) : null}

      {!query.isLoading && !query.isError && items.length > 0 && view === 'kanban' ? (
        <AgreementsKanban items={items} onOpen={openPurchase} />
      ) : null}
      {!query.isLoading && !query.isError && items.length > 0 && view === 'list' ? (
        <AgreementsList items={items} onOpen={openPurchase} />
      ) : null}
      {!query.isLoading && !query.isError && view === 'activities' ? (
        <AgreementsActivities projectGroup={projectGroup} items={items} onOpenAgreement={openAgreement} />
      ) : null}
      {!query.isLoading && !query.isError && view === 'calendar' ? (
        <AgreementsCalendar projectGroup={projectGroup} items={items} onOpenAgreement={openAgreement} />
      ) : null}
    </div>
  );
}
