'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import {
  crmCompaniesMutations,
  crmCompaniesQueries,
  crmCompaniesQueryKeys,
} from '@/lib/query/crm-companies-queries';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { fetchCrmCompanyHierarchy, fetchCrmCompanyTimeline } from '@/workspaces/crm/api/companies';

import { CrmAnalyticsStrip } from './g2/crm-analytics-strip';

const DETAIL_TABS = [
  'overview',
  'contacts',
  'timeline',
  'relationships',
  'hierarchy',
  'compliance',
  'audit',
] as const;

type DetailTab = (typeof DETAIL_TABS)[number];

export function CrmCompanyDetailView({ companyId }: { companyId: string }) {
  const t = useTranslations('crm.companies');
  const tCrm = useTranslations('crm');
  const tCommon = useTranslations('common');
  const { authLoading, user, canReadCompanies: canView } = useCrmAccess();
  const { openContact } = useContactCard();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const canQuery = !authLoading && canView;

  const detailQuery = useQuery({
    ...crmCompaniesQueries.detail(companyId),
    enabled: canQuery && Boolean(companyId),
  });

  const timelineQuery = useQuery({
    queryKey: crmCompaniesQueryKeys.timeline(companyId),
    queryFn: () => fetchCrmCompanyTimeline(companyId),
    enabled: canQuery && activeTab === 'timeline',
  });

  const hierarchyQuery = useQuery({
    queryKey: crmCompaniesQueryKeys.hierarchy(),
    queryFn: fetchCrmCompanyHierarchy,
    enabled: canQuery && activeTab === 'hierarchy',
  });

  const archiveMutation = useMutation({
    ...crmCompaniesMutations.archive(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: crmCompaniesQueryKeys.all });
    },
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={tCrm('accessDenied')} message={tCrm('accessDeniedHint')} />;
  }

  if (detailQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={tCrm('loadFailed')}
        message={detailQuery.error?.message ?? tCrm('loadFailed')}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const company = detailQuery.data;

  return (
    <div className="crm-company-detail" data-testid="crm-g2-company-detail">
      <header className="crm-company-detail__header">
        <div>
          <p className="crm-company-detail__eyebrow">{t(`companyTypes.${company.company_type}` as 'companyTypes.other')}</p>
          <h1>{company.display_name}</h1>
          {company.legal_name ? <p className="crm-company-detail__legal">{company.legal_name}</p> : null}
        </div>
        <div className="crm-company-detail__actions">
          {canUpdateCrm(user) ? (
            <Button
              type="button"
              variant="secondary"
              onClick={() => archiveMutation.mutate(companyId)}
              disabled={archiveMutation.isPending}
            >
              {t('actions.archive')}
            </Button>
          ) : null}
          <Link href={'/workspaces/crm/companies' as Route} className="ih-btn ih-btn--secondary">
            {t('actions.backToList')}
          </Link>
        </div>
      </header>

      <CrmAnalyticsStrip
        contactCount={company.contact_count ?? 0}
        activityCount={4}
        pipelineValue={company.industry ?? '—'}
        contactTrend={[2, 3, 4, 5, 6, 7, Math.max(1, company.contact_count ?? 8)]}
      />

      <nav className="crm-company-detail__tabs" aria-label={t('tabs.label')}>
        {DETAIL_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? 'crm-tab crm-tab--active' : 'crm-tab'}
            onClick={() => setActiveTab(tab)}
          >
            {t(`tabs.${tab}` as 'tabs.overview')}
          </button>
        ))}
      </nav>

      <div className="crm-company-detail__panel">
        {activeTab === 'overview' ? (
          <dl className="crm-detail-grid">
            <div><dt>{tCrm('fields.email')}</dt><dd>{company.primary_email ?? '—'}</dd></div>
            <div><dt>{tCrm('fields.phone')}</dt><dd>{company.primary_phone ?? '—'}</dd></div>
            <div><dt>{t('fields.domain')}</dt><dd>{company.domain ?? '—'}</dd></div>
            <div><dt>{t('fields.industry')}</dt><dd>{company.industry ?? '—'}</dd></div>
            <div><dt>{tCrm('fields.status')}</dt><dd>{tCrm(`statuses.${company.status}` as 'statuses.active')}</dd></div>
            <div><dt>{t('fields.contacts')}</dt><dd>{company.contact_count}</dd></div>
            {company.description ? (
              <div className="crm-detail-grid__full"><dt>{t('form.description')}</dt><dd>{company.description}</dd></div>
            ) : null}
          </dl>
        ) : null}

        {activeTab === 'contacts' ? (
          company.contacts.length === 0 ? (
            <EmptyState title={t('contacts.empty')} description={t('contacts.emptyHint')} />
          ) : (
            <table className="crm-contacts-table">
              <thead>
                <tr>
                  <th>{tCrm('fields.displayName')}</th>
                  <th>{t('contacts.role')}</th>
                  <th>{t('contacts.jobTitle')}</th>
                  <th>{t('contacts.primary')}</th>
                </tr>
              </thead>
              <tbody>
                {company.contacts.map((contact) => (
                  <tr key={contact.id}>
                    <td>
                      <button
                        type="button"
                        className="crm-company-detail__contact-link"
                        onClick={() => openContact(contact.contact_id)}
                      >
                        {contact.contact_display_name ?? contact.contact_id}
                      </button>
                    </td>
                    <td>{contact.role}</td>
                    <td>{contact.job_title ?? '—'}</td>
                    <td>{contact.is_primary ? tCommon('yes') : tCommon('no')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : null}

        {activeTab === 'timeline' ? (
          timelineQuery.isLoading ? (
            <LoadingState label={tCommon('loading')} />
          ) : !timelineQuery.data?.items.length ? (
            <EmptyState title={t('timeline.empty')} description={t('timeline.emptyHint')} />
          ) : (
            <ul className="crm-timeline-list">
              {timelineQuery.data.items.map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.description_key}</strong>
                  <span>{entry.actor_name ?? tCrm('systemActor')}</span>
                  <time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString()}</time>
                </li>
              ))}
            </ul>
          )
        ) : null}

        {activeTab === 'relationships' ? (
          company.relationships.length === 0 ? (
            <EmptyState title={t('relationships.empty')} description={t('relationships.emptyHint')} />
          ) : (
            <ul className="crm-relationship-list">
              {company.relationships.map((rel) => (
                <li key={rel.id}>
                  {rel.target_display_name ?? rel.target_company_id} — {rel.relationship_type}
                </li>
              ))}
            </ul>
          )
        ) : null}

        {activeTab === 'hierarchy' ? (
          hierarchyQuery.isLoading ? (
            <LoadingState label={tCommon('loading')} />
          ) : (
            <HierarchyTree nodes={hierarchyQuery.data?.roots ?? []} currentId={companyId} t={t} />
          )
        ) : null}

        {activeTab === 'compliance' ? (
          company.compliance_data ? (
            <pre className="crm-json-preview">{JSON.stringify(company.compliance_data, null, 2)}</pre>
          ) : (
            <EmptyState title={t('compliance.empty')} description={t('compliance.emptyHint')} />
          )
        ) : null}

        {activeTab === 'audit' ? (
          <p className="crm-dashboard__list-item-meta">{t('audit.hint')}</p>
        ) : null}
      </div>
    </div>
  );
}

function HierarchyTree({
  nodes,
  currentId,
  t,
}: {
  nodes: Array<{ id: string; display_name: string; children: typeof nodes }>;
  currentId: string;
  t: ReturnType<typeof useTranslations<'crm.companies'>>;
}) {
  if (nodes.length === 0) {
    return <EmptyState title={t('hierarchy.empty')} description={t('hierarchy.emptyHint')} />;
  }
  return (
    <ul className="crm-hierarchy-tree">
      {nodes.map((node) => (
        <li key={node.id} className={node.id === currentId ? 'crm-hierarchy-tree__current' : undefined}>
          {node.display_name}
          {node.children.length > 0 ? <HierarchyTree nodes={node.children} currentId={currentId} t={t} /> : null}
        </li>
      ))}
    </ul>
  );
}
