import type { MarketingCampaignStatus } from '@/workspaces/marketing/types';
import type { StatusChipTone } from '@investhome/ui';

export function campaignStatusTone(status: MarketingCampaignStatus): StatusChipTone {
  switch (status) {
    case 'active':
    case 'approved':
    case 'completed':
      return 'success';
    case 'pending_approval':
    case 'paused':
    case 'planning':
      return 'warning';
    case 'cancelled':
    case 'archived':
      return 'danger';
    default:
      return 'default';
  }
}
