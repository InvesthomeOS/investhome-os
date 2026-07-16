'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchProposalActivities, type SalesProposalDetail } from '@/lib/api/sales-proposals';

interface ActivityRow {
  id: string;
  activity_type: string;
  created_at: string;
}

export function ProposalActivityTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.activity');
  const [activities, setActivities] = useState<ActivityRow[]>([]);

  const load = useCallback(async () => {
    const rows = await fetchProposalActivities(proposal.id);
    setActivities(rows);
  }, [proposal.id]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <ul className="proposal-activity-list">
      {activities.map((row) => (
        <li key={row.id}>
          <strong>{row.activity_type}</strong>
          <span>{new Date(row.created_at).toLocaleString()}</span>
        </li>
      ))}
      {activities.length === 0 ? <li>{t('empty')}</li> : null}
    </ul>
  );
}
