'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchProposalVersions, type SalesProposalDetail, type SalesProposalVersion } from '@/lib/api/sales-proposals';

export function ProposalVersionsTab({ proposal }: { proposal: SalesProposalDetail }) {
  const t = useTranslations('salesProposals.versions');
  const [versions, setVersions] = useState<SalesProposalVersion[]>([]);

  const load = useCallback(async () => {
    const rows = await fetchProposalVersions(proposal.id);
    setVersions(rows);
  }, [proposal.id]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <ul className="proposal-versions-list">
      {versions.map((version) => (
        <li key={version.id}>
          <strong>{t('version', { number: version.version_number })}</strong>
          {version.is_approved ? ` · ${t('approved')}` : ''}
          <span>{new Date(version.created_at).toLocaleString()}</span>
        </li>
      ))}
    </ul>
  );
}
