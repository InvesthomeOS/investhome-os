'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { Button, StatusChip, Tabs } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  createProposalVersion,
  markProposalAccepted,
  markProposalRejected,
  markProposalSent,
  markProposalViewed,
  refreshProposalPricing,
  submitProposal,
  type SalesProposalDetail,
} from '@/lib/api/sales-proposals';
import { useSalesProposalLabels } from '@/lib/i18n/sales-proposal-labels';

import { ProposalActivityTab } from './activity-tab';
import { ProposalApprovalTab } from './approval-tab';
import { ProposalBrandingTab } from './branding-tab';
import { ProposalDocumentsTab } from './documents-tab';
import { ProposalItemsTab } from './items-tab';
import { ProposalOverviewTab } from './proposal-overview-tab';
import { ProposalPreviewTab } from './preview-tab';
import { ProposalPricingTab } from './pricing-tab';
import { ProposalRecipientTab } from './recipient-tab';
import { StaleWarningBanner } from './stale-warning-banner';
import { ProposalTermsTab } from './terms-tab';
import { ProposalVersionsTab } from './versions-tab';

type BuilderTab =
  | 'overview'
  | 'recipient'
  | 'items'
  | 'pricing'
  | 'terms'
  | 'documents'
  | 'branding'
  | 'preview'
  | 'approval'
  | 'versions'
  | 'activity';

interface ProposalBuilderProps {
  proposal: SalesProposalDetail;
  onReload: () => Promise<void>;
}

export function ProposalBuilder({ proposal, onReload }: ProposalBuilderProps) {
  const t = useTranslations('salesProposals');
  const { getStatusLabel, getErrorMessage, tTabs, tActions } = useSalesProposalLabels();
  const { user } = useAuth();
  const [tab, setTab] = useState<BuilderTab>('overview');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAction = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        await onReload();
      } catch (err) {
        const message =
          err instanceof ApiError
            ? getErrorMessage(err.message, err.message)
            : t('actionError');
        setError(message);
      } finally {
        setBusy(false);
      }
    },
    [getErrorMessage, onReload, t],
  );

  const tabs = [
    { id: 'overview' as const, label: tTabs('overview') },
    { id: 'recipient' as const, label: tTabs('recipient') },
    { id: 'items' as const, label: tTabs('items') },
    { id: 'pricing' as const, label: tTabs('pricing') },
    { id: 'terms' as const, label: tTabs('terms') },
    { id: 'documents' as const, label: tTabs('documents') },
    { id: 'branding' as const, label: tTabs('branding') },
    { id: 'preview' as const, label: tTabs('preview') },
    { id: 'approval' as const, label: tTabs('approval') },
    { id: 'versions' as const, label: tTabs('versions') },
    { id: 'activity' as const, label: tTabs('activity') },
  ];

  return (
    <div className="proposal-builder">
      <header className="proposal-builder-header">
        <div>
          <Link href="/dashboard/sales">{t('backToSales')}</Link>
          <h1>{proposal.title}</h1>
          <p>{proposal.proposal_number}</p>
          <StatusChip tone="default">{getStatusLabel(proposal.status)}</StatusChip>
        </div>
        <div className="proposal-builder-actions">
          {(proposal.status === 'draft' || proposal.status === 'revision_requested') &&
          hasPermission(user, 'sales', 'submit_proposal') ? (
            <Button disabled={busy} onClick={() => void runAction(() => submitProposal(proposal.id))}>
              {tActions('submit')}
            </Button>
          ) : null}
          {proposal.status === 'approved' && hasPermission(user, 'sales', 'mark_proposal_sent') ? (
            <Button disabled={busy} onClick={() => void runAction(() => markProposalSent(proposal.id))}>
              {tActions('markSent')}
            </Button>
          ) : null}
          {proposal.status === 'sent' && hasPermission(user, 'sales', 'mark_proposal_viewed') ? (
            <Button disabled={busy} onClick={() => void runAction(() => markProposalViewed(proposal.id))}>
              {tActions('markViewed')}
            </Button>
          ) : null}
          {(proposal.status === 'sent' || proposal.status === 'viewed') &&
          hasPermission(user, 'sales', 'mark_proposal_accepted') ? (
            <>
              <Button disabled={busy} onClick={() => void runAction(() => markProposalAccepted(proposal.id))}>
                {tActions('markAccepted')}
              </Button>
              <Button disabled={busy} onClick={() => void runAction(() => markProposalRejected(proposal.id))}>
                {tActions('markRejected')}
              </Button>
            </>
          ) : null}
          {['approved', 'sent', 'viewed', 'revision_requested'].includes(proposal.status) &&
          hasPermission(user, 'sales', 'update_proposal') ? (
            <Button disabled={busy} onClick={() => void runAction(() => createProposalVersion(proposal.id))}>
              {tActions('newVersion')}
            </Button>
          ) : null}
        </div>
      </header>

      <StaleWarningBanner
        proposal={proposal}
        refreshing={busy}
        onRefresh={
          hasPermission(user, 'sales', 'update_proposal')
            ? () => void runAction(() => refreshProposalPricing(proposal.id))
            : undefined
        }
      />

      {error ? <p className="error-text">{error}</p> : null}

      <Tabs tabs={tabs} activeId={tab} onChange={(value) => setTab(value as BuilderTab)} ariaLabel={t('builderAriaLabel')} />

      <div className="proposal-builder-panel">
        {tab === 'overview' ? <ProposalOverviewTab proposal={proposal} /> : null}
        {tab === 'recipient' ? <ProposalRecipientTab proposal={proposal} /> : null}
        {tab === 'items' ? <ProposalItemsTab proposal={proposal} /> : null}
        {tab === 'pricing' ? <ProposalPricingTab proposal={proposal} /> : null}
        {tab === 'terms' ? <ProposalTermsTab proposal={proposal} /> : null}
        {tab === 'documents' ? <ProposalDocumentsTab /> : null}
        {tab === 'branding' ? <ProposalBrandingTab proposal={proposal} /> : null}
        {tab === 'preview' ? <ProposalPreviewTab proposal={proposal} /> : null}
        {tab === 'approval' ? <ProposalApprovalTab proposal={proposal} onUpdated={() => void onReload()} /> : null}
        {tab === 'versions' ? <ProposalVersionsTab proposal={proposal} /> : null}
        {tab === 'activity' ? <ProposalActivityTab proposal={proposal} /> : null}
      </div>
    </div>
  );
}
