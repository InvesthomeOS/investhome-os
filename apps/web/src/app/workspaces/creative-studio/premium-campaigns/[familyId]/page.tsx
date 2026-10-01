'use client';

import { useParams } from 'next/navigation';

import { PremiumCampaignWorkspace } from '../premium-campaign-workspace';

export default function PremiumCampaignPage() {
  const params = useParams<{ familyId: string }>();
  return <PremiumCampaignWorkspace familyId={String(params.familyId)} />;
}
