'use client';

import { useTranslations } from 'next-intl';

import type { ReadinessCaseStatus, ReadinessRequirementStatus, ReadinessViewName } from '@/lib/api/sales-readiness';

export function useReadinessLabels() {
  const t = useTranslations('salesReadiness');

  const viewOptions: ReadinessViewName[] = [
    'overview',
    'in_progress',
    'blocked',
    'deposit_pending',
    'documents_missing',
    'signature_pending',
    'ready_for_handoff',
    'handed_off',
    'archived',
  ];

  const getViewLabel = (view: ReadinessViewName) => t(`views.${view}` as never);

  const getStatusLabel = (status: ReadinessCaseStatus) => t(`status.${status}` as never);

  const getRequirementStatusLabel = (status: ReadinessRequirementStatus) =>
    t(`requirementStatus.${status}` as never);

  const getGroupLabel = (group: string) => t(`groups.${group}` as never);

  return { viewOptions, getViewLabel, getStatusLabel, getRequirementStatusLabel, getGroupLabel };
}
