'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Drawer, StatusChip, Tabs } from '@investhome/ui';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { hasPermission } from '@/lib/api/auth';
import {
  approveHandoff,
  fetchReadinessCase,
  fetchReadinessStatusHistory,
  markSignaturePending,
  recalculateReadinessCase,
  requestHandoff,
  returnHandoff,
  verifyRequirement,
  type ReadinessCase,
  type ReadinessRequirement,
  type ReadinessStatusHistoryEntry,
} from '@/lib/api/sales-readiness';
import { useAuth } from '@/lib/auth/auth-context';
import { useReadinessLabels } from '@/lib/i18n/sales-readiness-labels';

import { HandoffApproveModal } from './handoff-approve-modal';
import { HandoffRequestModal } from './handoff-request-modal';
import { RequirementsChecklist } from './requirements-checklist';
import { WaiverModal } from './waiver-modal';

type DetailTab =
  | 'overview'
  | 'reservation'
  | 'deposit'
  | 'party'
  | 'documents'
  | 'contract'
  | 'signature'
  | 'handoff'
  | 'requirements'
  | 'activity'
  | 'statusHistory';

interface ReadinessDetailDrawerProps {
  caseId: string | null;
  open: boolean;
  onClose: () => void;
  onUpdated?: (item: ReadinessCase) => void;
}

export function ReadinessDetailDrawer({ caseId, open, onClose, onUpdated }: ReadinessDetailDrawerProps) {
  const t = useTranslations('salesReadiness');
  const { user } = useAuth();
  const { getStatusLabel } = useReadinessLabels();
  const [item, setItem] = useState<ReadinessCase | null>(null);
  const [history, setHistory] = useState<ReadinessStatusHistoryEntry[]>([]);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [loading, setLoading] = useState(false);
  const [waiverReq, setWaiverReq] = useState<ReadinessRequirement | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);
  const [approveOpen, setApproveOpen] = useState(false);

  const canVerify = user ? hasPermission(user, 'sales', 'verify_readiness') : false;
  const canRequestHandoff = user ? hasPermission(user, 'sales', 'request_handoff') : false;
  const canApproveHandoff = user ? hasPermission(user, 'sales', 'approve_handoff') : false;
  const canViewDeposit = user ? hasPermission(user, 'sales', 'view_deposit_status') : false;

  const load = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    try {
      const [detail, hist] = await Promise.all([
        fetchReadinessCase(caseId),
        fetchReadinessStatusHistory(caseId),
      ]);
      setItem(detail);
      setHistory(hist);
      onUpdated?.(detail);
    } finally {
      setLoading(false);
    }
  }, [caseId, onUpdated]);

  useEffect(() => {
    if (open && caseId) void load();
  }, [open, caseId, load]);

  const handleVerify = async (req: ReadinessRequirement) => {
    if (!caseId) return;
    await verifyRequirement(req.id);
    await load();
    await recalculateReadinessCase(caseId);
    await load();
  };

  const tabs = [
    { id: 'overview', label: t('tabs.overview') },
    { id: 'reservation', label: t('tabs.reservation') },
    { id: 'deposit', label: t('tabs.deposit') },
    { id: 'party', label: t('tabs.party') },
    { id: 'documents', label: t('tabs.documents') },
    { id: 'contract', label: t('tabs.contract') },
    { id: 'signature', label: t('tabs.signature') },
    { id: 'handoff', label: t('tabs.handoff') },
    { id: 'requirements', label: t('tabs.requirements') },
    { id: 'activity', label: t('tabs.activity') },
    { id: 'statusHistory', label: t('tabs.statusHistory') },
  ];

  return (
    <>
      <Drawer open={open} onClose={onClose} title={item?.case_code ?? t('detail.title')} wide>
        {loading && <p>{t('loading')}</p>}
        {item && (
          <>
            <div className="readiness-detail__header">
              <StatusChip tone={item.status === 'blocked' ? 'warning' : 'default'}>
                {getStatusLabel(item.status)}
              </StatusChip>
              <span>{item.readiness_percentage}%</span>
              {item.blocker_summary && <p className="readiness-detail__blocker">{item.blocker_summary}</p>}
            </div>
            <Tabs
              tabs={tabs}
              activeId={activeTab}
              onChange={(id) => setActiveTab(id as DetailTab)}
            />
            {activeTab === 'overview' && (
              <dl className="readiness-detail__fields">
                <div><dt>{t('fields.opportunity')}</dt><dd>{item.opportunity_code}</dd></div>
                <div><dt>{t('fields.party')}</dt><dd>{item.party_name ?? '—'}</dd></div>
                <div><dt>{t('fields.asset')}</dt><dd>{item.inventory_display_id ?? '—'}</dd></div>
                <div><dt>{t('fields.targetContract')}</dt><dd>{item.target_contract_date ?? '—'}</dd></div>
                <div><dt>{t('fields.targetHandoff')}</dt><dd>{item.target_closing_handoff_date ?? '—'}</dd></div>
                <div><dt>{t('fields.missingMandatory')}</dt><dd>{item.missing_mandatory_count ?? 0}</dd></div>
              </dl>
            )}
            {activeTab === 'deposit' && canViewDeposit && (
              <dl className="readiness-detail__fields">
                <div><dt>{t('deposit.required')}</dt><dd>{item.deposit_summary?.deposit_amount ?? '—'}</dd></div>
                <div><dt>{t('deposit.received')}</dt><dd>{item.deposit_summary?.received_amount ?? '—'}</dd></div>
                <div><dt>{t('deposit.remaining')}</dt><dd>{item.deposit_summary?.remaining_amount ?? '—'}</dd></div>
                <div><dt>{t('deposit.currency')}</dt><dd>{item.deposit_summary?.currency ?? '—'}</dd></div>
                <div><dt>{t('deposit.overdue')}</dt><dd>{item.deposit_summary?.is_overdue ? t('yes') : t('no')}</dd></div>
              </dl>
            )}
            {activeTab === 'signature' && (
              <div>
                <p>{t('signature.manualNotice')}</p>
                <p>{t('signature.status')}: {item.signature_status ?? t('signature.notRequested')}</p>
                {canVerify && (
                  <Button variant="secondary" onClick={() => markSignaturePending(item.id).then(load)}>
                    {t('signature.markPending')}
                  </Button>
                )}
              </div>
            )}
            {activeTab === 'handoff' && (
              <div className="readiness-detail__handoff">
                <p>{t('handoff.checklistIntro')}</p>
                {canRequestHandoff && item.status !== 'handed_off' && (
                  <Button variant="primary" onClick={() => setHandoffOpen(true)}>{t('handoff.request')}</Button>
                )}
                {canApproveHandoff && item.handoff_requested_at && !item.handoff_approved_at && (
                  <Button variant="secondary" onClick={() => setApproveOpen(true)}>{t('handoff.review')}</Button>
                )}
                <Link href={`/dashboard/sales?opportunity=${item.opportunity_id}` as Route}>{t('handoff.openOpportunity')}</Link>
              </div>
            )}
            {(activeTab === 'requirements' || activeTab === 'documents' || activeTab === 'contract') && (
              <RequirementsChecklist
                requirements={item.requirements ?? []}
                onVerify={canVerify ? handleVerify : undefined}
                onWaive={canVerify ? (req) => setWaiverReq(req) : undefined}
              />
            )}
            {activeTab === 'activity' && item && (
              <EntityActivityTimeline entityType="sales_readiness" entityId={item.id} />
            )}
            {activeTab === 'statusHistory' && (
              <ul className="readiness-history">
                {history.map((entry) => (
                  <li key={entry.id}>
                    <strong>{entry.new_status}</strong>
                    {entry.previous_status && <span> ← {entry.previous_status}</span>}
                    {entry.reason && <p>{entry.reason}</p>}
                    <time>{new Date(entry.effective_at).toLocaleString()}</time>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </Drawer>
      <WaiverModal
        open={waiverReq !== null}
        requirementTitle={waiverReq?.title ?? ''}
        onClose={() => setWaiverReq(null)}
        onSubmit={async (reason) => {
          if (!waiverReq) return;
          const { waiveRequirement } = await import('@/lib/api/sales-readiness');
          await waiveRequirement(waiverReq.id, reason);
          setWaiverReq(null);
          await load();
        }}
      />
      <HandoffRequestModal
        open={handoffOpen}
        onClose={() => setHandoffOpen(false)}
        onSubmit={async (notes) => {
          if (!item) return;
          await requestHandoff(item.id, notes);
          setHandoffOpen(false);
          await load();
        }}
      />
      <HandoffApproveModal
        open={approveOpen}
        caseCode={item?.case_code ?? ''}
        onClose={() => setApproveOpen(false)}
        onApprove={async () => {
          if (!item) return;
          await approveHandoff(item.id);
          setApproveOpen(false);
          await load();
        }}
        onReturn={async () => {
          if (!item) return;
          setApproveOpen(false);
          const reason = window.prompt(t('handoff.returnReasonPrompt'));
          if (reason) {
            await returnHandoff(item.id, reason);
            await load();
          }
        }}
      />
    </>
  );
}
