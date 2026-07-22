'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams, usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canActivateCampaigns,
  canApproveCampaigns,
  canArchiveCampaigns,
  canManageCampaigns,
  canPauseCampaigns,
  canReadMarketing,
  canViewCampaignAnalytics,
  canViewCampaignAttribution,
  canViewCampaignBudget,
  canViewCampaignLeads,
  canViewMarketingAI,
} from '@/lib/marketing/marketing-permissions';
import { campaignQueries, campaignQueryKeys } from '@/workspaces/marketing/hooks/use-campaigns';
import {
  activateCampaign,
  archiveCampaign,
  pauseCampaign,
  submitCampaignApproval,
  approveCampaign,
} from '@/workspaces/marketing/api/campaigns';
import { CAMPAIGN_DETAIL_TABS, type CampaignDetailTab } from '@/workspaces/marketing/types';
import { campaignStatusTone } from '@/workspaces/marketing/utils/campaign-status';

import { CampaignOverviewPanel } from './campaign-overview-panel';
import { CampaignPlanningPanel } from './campaign-planning-panel';
import { CampaignBudgetPanel } from './campaign-budget-panel';
import { CampaignTrackingPanel } from './campaign-tracking-panel';
import { CampaignLeadsPanel } from './campaign-leads-panel';
import { CampaignShellPanel } from './campaign-shell-panel';
import { CampaignAssetsPanel } from './campaign-assets-panel';
import { CampaignPerformancePanel } from './campaign-performance-panel';

const STATUS_ACTIONS: Record<string, { action: string; permission: string }[]> = {
  draft: [{ action: 'submit_approval', permission: 'manage' }],
  planning: [{ action: 'submit_approval', permission: 'manage' }],
  pending_approval: [{ action: 'approve', permission: 'approve' }, { action: 'reject', permission: 'approve' }],
  approved: [{ action: 'activate', permission: 'activate' }, { action: 'schedule', permission: 'manage' }],
  scheduled: [{ action: 'activate', permission: 'activate' }],
  active: [{ action: 'pause', permission: 'pause' }, { action: 'complete', permission: 'manage' }],
  paused: [{ action: 'activate', permission: 'activate' }, { action: 'complete', permission: 'manage' }],
};

function tabPermission(tab: CampaignDetailTab, user: ReturnType<typeof useAuth>['user']): boolean {
  switch (tab) {
    case 'budget':
      return canViewCampaignBudget(user);
    case 'leads':
      return canViewCampaignLeads(user);
    case 'analytics':
      return canViewCampaignAnalytics(user);
    case 'attribution':
      return canViewCampaignAttribution(user);
    case 'approvals':
      return canApproveCampaigns(user) || canManageCampaigns(user);
    default:
      return canReadMarketing(user) || canManageCampaigns(user);
  }
}

export function CampaignDetailLayout({ children }: { children?: React.ReactNode }) {
  const params = useParams<{ campaignId: string }>();
  const pathname = usePathname();
  const campaignId = params.campaignId;
  const t = useTranslations('marketing.campaigns.detail');
  const tStatus = useTranslations('marketing.campaigns.status');
  const tActions = useTranslations('marketing.campaigns.actions');
  const tAi = useTranslations('marketing.ai.assistant');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const detailQuery = useQuery(campaignQueries.detail(campaignId));

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: campaignQueryKeys.detail(campaignId) });
    await queryClient.invalidateQueries({ queryKey: campaignQueryKeys.all });
  };

  const actionMutation = useMutation({
    mutationFn: async (action: string) => {
      switch (action) {
        case 'activate':
          return activateCampaign(campaignId);
        case 'pause':
          return pauseCampaign(campaignId);
        case 'submit_approval':
          return submitCampaignApproval(campaignId);
        case 'approve':
          return approveCampaign(campaignId);
        case 'archive':
          return archiveCampaign(campaignId, t('detail.archiveReason'));
        default:
          throw new Error(`Unknown action: ${action}`);
      }
    },
    onSuccess: invalidate,
  });

  if (!canReadMarketing(user) && !canManageCampaigns(user)) {
    return <EmptyState title={t('accessDenied')} />;
  }

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={tCommon('error')}
        message={detailQuery.error instanceof ApiError ? detailQuery.error.message : t('notFound')}
      />
    );
  }

  const campaign = detailQuery.data;
  const basePath = `/workspaces/marketing/campaigns/${campaignId}`;
  const currentTab = pathname.replace(basePath, '').replace(/^\//, '') || 'overview';
  const availableActions = STATUS_ACTIONS[campaign.status] ?? [];

  const renderTab = () => {
    if (children) return children;
    switch (currentTab as CampaignDetailTab) {
      case 'overview':
        return <CampaignOverviewPanel campaignId={campaignId} />;
      case 'planning':
        return <CampaignPlanningPanel campaignId={campaignId} />;
      case 'assets':
        return <CampaignAssetsPanel campaignId={campaignId} />;
      case 'budget':
        return <CampaignBudgetPanel campaignId={campaignId} />;
      case 'leads':
        return <CampaignLeadsPanel campaignId={campaignId} />;
      case 'attribution':
        return <CampaignPerformancePanel campaignId={campaignId} mode="attribution" />;
      case 'analytics':
        return <CampaignPerformancePanel campaignId={campaignId} mode="analytics" />;
      case 'settings':
        return <CampaignTrackingPanel campaignId={campaignId} />;
      default:
        return <CampaignShellPanel type={currentTab} campaignId={campaignId} />;
    }
  };

  return (
    <div>
      <div className="marketing-detail__header">
        <div>
          <h1 className="marketing-detail__title">{campaign.name}</h1>
          <div className="marketing-detail__meta">
            <StatusChip tone={campaignStatusTone(campaign.status)}>{tStatus(campaign.status)}</StatusChip>
            {campaign.code && <span>{campaign.code}</span>}
          </div>
        </div>
        <div className="marketing-detail__actions">
          {canViewMarketingAI(user) ? (
            <Link
              href={
                `/workspaces/marketing/ai/assistant?mode=campaign_analysis&campaignId=${campaignId}` as Route
              }
              className="button button--secondary"
            >
              {tAi('contextualEntry')}
            </Link>
          ) : null}
          {availableActions.map(({ action, permission }) => {
            const allowed =
              (permission === 'manage' && canManageCampaigns(user)) ||
              (permission === 'activate' && canActivateCampaigns(user)) ||
              (permission === 'pause' && canPauseCampaigns(user)) ||
              (permission === 'approve' && canApproveCampaigns(user));
            if (!allowed) return null;
            return (
              <Button
                key={action}
                variant={action === 'reject' ? 'secondary' : 'primary'}
                onClick={() => actionMutation.mutate(action)}
                disabled={actionMutation.isPending}
              >
                {tActions(action as 'activate')}
              </Button>
            );
          })}
          {canArchiveCampaigns(user) && campaign.status !== 'archived' && (
            <Button
              variant="ghost"
              onClick={() => actionMutation.mutate('archive')}
              disabled={actionMutation.isPending}
            >
              {tActions('archive')}
            </Button>
          )}
        </div>
      </div>

      <nav className="marketing-detail__nav">
        {CAMPAIGN_DETAIL_TABS.filter((tab) => tabPermission(tab, user)).map((tab) => {
          const href = tab === 'overview' ? basePath : `${basePath}/${tab}`;
          const isActive = currentTab === tab || (tab === 'overview' && currentTab === '');
          return (
            <Link
              key={tab}
              href={href as Route}
              className={isActive ? 'marketing-detail__nav-link marketing-detail__nav-link--active' : 'marketing-detail__nav-link'}
            >
              {t(`tabs.${tab}` as 'tabs.overview')}
            </Link>
          );
        })}
      </nav>

      {renderTab()}
    </div>
  );
}
