'use client';

import { useQuery } from '@tanstack/react-query';

import { whatsappQueries } from '@/workspaces/marketing/api/whatsapp';

import { ChannelWorkspace } from '../../_components/channel-workspace';

export function WhatsAppWorkspace() {
  const dashboardQuery = useQuery(whatsappQueries.dashboard());
  const listQuery = useQuery(whatsappQueries.list());

  return (
    <ChannelWorkspace
      channelKey="whatsapp"
      permission="send_whatsapp"
      dashboardQuery={dashboardQuery}
      listQuery={listQuery}
      detailBasePath="/workspaces/marketing/whatsapp/campaigns"
      createPath="/workspaces/marketing/whatsapp/campaigns/new"
    />
  );
}
