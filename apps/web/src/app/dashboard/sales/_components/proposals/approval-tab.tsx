'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchProposalApprovals, reviewProposal, type SalesProposalDetail } from '@/lib/api/sales-proposals';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

interface ApprovalRecord {
  id: string;
  decision: string;
  comments: string | null;
  created_at: string;
}

export function ProposalApprovalTab({
  proposal,
  onUpdated,
}: {
  proposal: SalesProposalDetail;
  onUpdated: () => void;
}) {
  const t = useTranslations('salesProposals.approval');
  const { user } = useAuth();
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [comments, setComments] = useState('');
  const [busy, setBusy] = useState(false);

  const canReview = hasPermission(user, 'sales', 'review_proposal');

  const load = useCallback(async () => {
    const rows = await fetchProposalApprovals(proposal.id);
    setApprovals(rows);
  }, [proposal.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleReview = async (decision: 'approved' | 'rejected' | 'revision_requested') => {
    setBusy(true);
    try {
      await reviewProposal(proposal.id, decision, comments || undefined);
      onUpdated();
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      {proposal.status === 'internal_review' && canReview ? (
        <div className="proposal-approval-actions">
          <textarea value={comments} onChange={(e) => setComments(e.target.value)} placeholder={t('commentsPlaceholder')} />
          <button type="button" disabled={busy} onClick={() => void handleReview('approved')}>{t('approve')}</button>
          <button type="button" disabled={busy} onClick={() => void handleReview('revision_requested')}>{t('revision')}</button>
          <button type="button" disabled={busy} onClick={() => void handleReview('rejected')}>{t('reject')}</button>
        </div>
      ) : null}
      <ul>
        {approvals.map((row) => (
          <li key={row.id}>
            <strong>{row.decision}</strong> — {new Date(row.created_at).toLocaleString()}
            {row.comments ? <p>{row.comments}</p> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
