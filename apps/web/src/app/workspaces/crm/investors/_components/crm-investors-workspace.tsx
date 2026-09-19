'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { LoadingState } from '@investhome/ui';

import { CrmPeopleWorkspace } from '@/app/workspaces/crm/people/_components/crm-people-workspace';
import type { PeopleWorkspacePreview } from '@/app/workspaces/crm/people/people-model';
import { fetchContacts } from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { buildInvestorsPreview } from '@/workspaces/crm/lib/map-live-workspace';

export function CrmInvestorsWorkspace({
  preview: previewProp,
  onOpenAi,
  detailBasePath = '/workspaces/crm/investors',
}: {
  preview?: PeopleWorkspacePreview;
  onOpenAi?: (prompt?: string) => void;
  detailBasePath?: string;
}) {
  const t = useTranslations('crm.investorsWorkspace');
  const { openContact } = useContactCard();
  const liveQuery = useQuery({
    queryKey: ['crm', 'contacts', 'investors'],
    queryFn: () =>
      fetchContacts({
        category: 'agreement',
        page: 1,
        page_size: 100,
        sort_by: 'last_contact_at',
        sort_dir: 'desc',
      }),
    enabled: !previewProp,
  });
  const preview =
    previewProp ?? buildInvestorsPreview(liveQuery.data?.items ?? [], liveQuery.data?.total ?? 0, 20);

  if (!previewProp && liveQuery.isLoading) {
    return <LoadingState label={t('title')} />;
  }

  return (
    <CrmPeopleWorkspace
      preview={preview}
      onOpenAi={onOpenAi}
      onOpenPerson={openContact}
      detailBasePath={detailBasePath}
      newPersonHref="/workspaces/crm/contacts/new"
      titleOverride={t('title')}
      subtitleOverride={t('subtitle')}
      testId="crm-investors-workspace"
    />
  );
}
