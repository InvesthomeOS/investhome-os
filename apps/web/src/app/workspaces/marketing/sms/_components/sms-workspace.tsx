'use client';

import { useQuery } from '@tanstack/react-query';

import { smsQueries } from '@/workspaces/marketing/api/sms';

import { ChannelWorkspace } from '../../_components/channel-workspace';

export function SmsWorkspace() {
  const dashboardQuery = useQuery(smsQueries.dashboard());
  const listQuery = useQuery(smsQueries.list());

  return (
    <ChannelWorkspace
      channelKey="sms"
      permission="send_sms"
      dashboardQuery={dashboardQuery}
      listQuery={listQuery}
      detailBasePath="/workspaces/marketing/sms/campaigns"
      createPath="/workspaces/marketing/sms/campaigns/new"
    />
  );
}
