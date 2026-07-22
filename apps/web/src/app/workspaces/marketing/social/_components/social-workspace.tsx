'use client';

import { useQuery } from '@tanstack/react-query';

import { socialQueries } from '@/workspaces/marketing/api/social';

import { ChannelWorkspace } from '../../_components/channel-workspace';

export function SocialWorkspace() {
  const dashboardQuery = useQuery(socialQueries.dashboard());
  const listQuery = useQuery(socialQueries.list());

  return (
    <ChannelWorkspace
      channelKey="social"
      permission="publish_content"
      dashboardQuery={dashboardQuery}
      listQuery={listQuery}
      detailBasePath="/workspaces/marketing/social/posts"
      createPath="/workspaces/marketing/social/posts/new"
      nameField="title"
    />
  );
}
