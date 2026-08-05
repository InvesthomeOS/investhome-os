'use client';

import { useTranslations } from 'next-intl';

import { CrmPeopleWorkspace } from '@/app/workspaces/crm/people/_components/crm-people-workspace';
import type { PeopleWorkspacePreview } from '@/app/workspaces/crm/people/people-model';

export function CrmInvestorsWorkspace({
  preview,
  onOpenAi,
  detailBasePath = '/workspaces/crm/investors',
}: {
  preview: PeopleWorkspacePreview;
  onOpenAi?: (prompt?: string) => void;
  detailBasePath?: string;
}) {
  const t = useTranslations('crm.investorsWorkspace');

  return (
    <CrmPeopleWorkspace
      preview={preview}
      onOpenAi={onOpenAi}
      detailBasePath={detailBasePath}
      newPersonHref="/workspaces/crm/contacts/new"
      titleOverride={t('title')}
      subtitleOverride={t('subtitle')}
      testId="crm-investors-workspace"
    />
  );
}
