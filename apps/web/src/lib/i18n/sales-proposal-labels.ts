import { useTranslations } from 'next-intl';

import { PROPOSAL_STATUSES, type ProposalStatus } from '@/lib/api/sales-proposals';

export function useSalesProposalLabels() {
  const tStatus = useTranslations('salesProposals.statuses');
  const tTabs = useTranslations('salesProposals.tabs');
  const tActions = useTranslations('salesProposals.actions');
  const tErrors = useTranslations('salesProposals.errors');

  const getStatusLabel = (value: ProposalStatus | string) =>
    tStatus(value as ProposalStatus);

  const statusOptions = PROPOSAL_STATUSES.map((status) => ({
    value: status,
    label: tStatus(status),
  }));

  const getErrorMessage = (errorKey: string | undefined, fallback: string) => {
    if (!errorKey) return fallback;
    const key = errorKey.startsWith('sales.proposal.errors.')
      ? errorKey.slice('sales.proposal.errors.'.length)
      : errorKey.replace('sales.proposal.errors.', '');
    try {
      return tErrors(key as never);
    } catch {
      return fallback;
    }
  };

  return {
    getStatusLabel,
    statusOptions,
    getErrorMessage,
    tTabs,
    tActions,
  };
}
