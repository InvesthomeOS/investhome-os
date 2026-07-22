'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, Tabs } from '@investhome/ui';

import { canArchiveCrm, canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { archiveContact, restoreContact } from '@/workspaces/crm/api/contacts';
import { contactQueries, contactQueryKeys } from '@/workspaces/crm/hooks/use-contacts';

import { CrmAnalyticsStrip } from '../../_components/g2/crm-analytics-strip';

type ContactDetailViewProps = {
  contactId: string;
};

export function ContactDetailView({ contactId }: ContactDetailViewProps) {
  const t = useTranslations('crm.contacts.detail');
  const tTypes = useTranslations('crm.contactTypes');
  const tCommon = useTranslations('common');
  const { authLoading, user, canRead } = useCrmAccess();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('overview');
  const detailQuery = useQuery({
    ...contactQueries.detail(contactId),
    enabled: !authLoading && canRead,
  });

  const actionMutation = useMutation({
    mutationFn: async (action: 'archive' | 'restore') =>
      action === 'archive' ? archiveContact(contactId) : restoreContact(contactId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: contactQueryKeys.detail(contactId) });
    },
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canRead) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  if (detailQuery.isLoading) {
    return <LoadingState label={t('loading')} />;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={t('loadError')}
        message={detailQuery.error?.message ?? t('loadError')}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const contact = detailQuery.data;

  return (
    <div className="crm-contact-detail" data-testid="crm-g2-contact-detail">
      <header className="crm-contact-detail__header">
        <div>
          <p className="company-workspace__eyebrow">{tTypes(contact.contact_type)}</p>
          <h1>{contact.display_name}</h1>
          <p>{contact.organization_name ?? contact.company_name ?? contact.primary_email ?? '—'}</p>
        </div>
        <div className="company-workspace__header-actions">
          {canArchiveCrm(user) && contact.status !== 'archived' ? (
            <Button type="button" variant="secondary" onClick={() => actionMutation.mutate('archive')}>
              {t('archive')}
            </Button>
          ) : null}
          {canUpdateCrm(user) && contact.status === 'archived' ? (
            <Button type="button" onClick={() => actionMutation.mutate('restore')}>
              {t('restore')}
            </Button>
          ) : null}
        </div>
      </header>

      <CrmAnalyticsStrip
        contactCount={1}
        activityCount={contact.relationship_score ?? 0}
        pipelineValue={String(contact.engagement_score ?? 0)}
        contactTrend={[2, 3, 4, 5, 6, 7, 8]}
        activityTrend={[1, 2, 2, 3, 4, 5, Math.max(1, contact.relationship_score ?? 6)]}
      />

      <Tabs
        activeId={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: 'overview', label: t('tabs.overview') },
          { id: 'timeline', label: t('tabs.timeline') },
          { id: 'relationships', label: t('tabs.relationships') },
          { id: 'compliance', label: t('tabs.compliance') },
        ]}
      />

      {activeTab === 'overview' ? (
        <div className="crm-contact-detail__grid">
          <article className="crm-contact-detail__card">
            <h3>{t('sections.contact')}</h3>
            <dl>
              <dt>{t('fields.email')}</dt>
              <dd>{contact.primary_email ?? '—'}</dd>
              <dt>{t('fields.phone')}</dt>
              <dd>{contact.primary_phone ?? '—'}</dd>
              <dt>{t('fields.owner')}</dt>
              <dd>{contact.owner_name ?? '—'}</dd>
            </dl>
          </article>
          <article className="crm-contact-detail__card">
            <h3>{t('sections.relationship')}</h3>
            <dl>
              <dt>{t('fields.lifecycle')}</dt>
              <dd>{contact.lifecycle_stage}</dd>
              <dt>{t('fields.score')}</dt>
              <dd>{contact.relationship_score}</dd>
              <dt>{t('fields.engagement')}</dt>
              <dd>{contact.engagement_score}</dd>
            </dl>
          </article>
          {contact.investment_profile ? (
            <article className="crm-contact-detail__card">
              <h3>{t('sections.investment')}</h3>
              <pre>{JSON.stringify(contact.investment_profile, null, 2)}</pre>
            </article>
          ) : null}
          {contact.buyer_profile ? (
            <article className="crm-contact-detail__card">
              <h3>{t('sections.buyer')}</h3>
              <pre>{JSON.stringify(contact.buyer_profile, null, 2)}</pre>
            </article>
          ) : null}
          {contact.notes ? (
            <article className="crm-contact-detail__card">
              <h3>{t('sections.notes')}</h3>
              <p>{contact.notes}</p>
            </article>
          ) : null}
        </div>
      ) : null}

      {activeTab === 'timeline' ? (
        <EmptyState title={t('timelineEmpty')} description={t('timelineEmptyHint')} />
      ) : null}
      {activeTab === 'relationships' ? (
        <EmptyState title={t('relationshipsEmpty')} description={t('relationshipsEmptyHint')} />
      ) : null}
      {activeTab === 'compliance' ? (
        contact.compliance_data ? (
          <pre>{JSON.stringify(contact.compliance_data, null, 2)}</pre>
        ) : (
          <EmptyState title={t('complianceEmpty')} description={t('complianceEmptyHint')} />
        )
      ) : null}
    </div>
  );
}
