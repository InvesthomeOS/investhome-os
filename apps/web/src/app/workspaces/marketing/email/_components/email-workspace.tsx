'use client';

import { useQuery } from '@tanstack/react-query';

import { emailQueries } from '@/workspaces/marketing/api/email';

import { ChannelWorkspace } from '../../_components/channel-workspace';

export function EmailWorkspace() {
  const dashboardQuery = useQuery(emailQueries.dashboard());
  const listQuery = useQuery(emailQueries.list());

  return (
    <ChannelWorkspace
      channelKey="email"
      permission="send_email"
      dashboardQuery={dashboardQuery}
      listQuery={listQuery}
      detailBasePath="/workspaces/marketing/email/campaigns"
      createPath="/workspaces/marketing/email/campaigns/new"
    />
  );
}
