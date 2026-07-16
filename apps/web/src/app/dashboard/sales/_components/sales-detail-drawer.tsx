'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Drawer, StatusChip, Tabs } from '@investhome/ui';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import { fetchLead, type Lead } from '@/lib/api/leads';
import { fetchInvestor, type Investor } from '@/lib/api/investors';
import { fetchInventoryAsset, fetchReservation, type InventoryAsset, type InventoryReservation } from '@/lib/api/inventory';
import type { Project } from '@/lib/api/projects';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  fetchOpportunityTimeline,
  formatMoney,
  formatShortDate,
  type OpportunityTimelineEntry,
  type SalesOpportunity,
} from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

type DetailTab =
  | 'overview'
  | 'party'
  | 'projects'
  | 'inventory'
  | 'stageHistory'
  | 'nextActions'
  | 'reservations'
  | 'documents'
  | 'finance'
  | 'activity'
  | 'timeline';

interface SalesDetailDrawerProps {
  opportunity: SalesOpportunity | null;
  projects: Project[];
  linkedProjectIds: string[];
  linkedInventoryIds: string[];
  partyName: string | null;
  assigneeName: string | null;
  archiving: boolean;
  canUpdate: boolean;
  canChangeStage: boolean;
  canChangeProbability: boolean;
  canArchive: boolean;
  canRestore: boolean;
  canViewSensitiveValue: boolean;
  onClose: () => void;
  onEdit: (opportunity: SalesOpportunity) => void;
  onArchive: (opportunity: SalesOpportunity) => void;
  onRestore: (opportunity: SalesOpportunity) => void;
  onChangeStage: (opportunity: SalesOpportunity) => void;
  onEditNextAction: (opportunity: SalesOpportunity) => void;
  onLinkProject: (opportunity: SalesOpportunity) => void;
  onLinkInventory: (opportunity: SalesOpportunity) => void;
}

function DetailField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function SalesDetailDrawer({
  opportunity,
  projects,
  linkedProjectIds,
  linkedInventoryIds,
  partyName,
  assigneeName,
  archiving,
  canUpdate,
  canChangeStage,
  canArchive,
  canRestore,
  canViewSensitiveValue,
  onClose,
  onEdit,
  onArchive,
  onRestore,
  onChangeStage,
  onEditNextAction,
  onLinkProject,
  onLinkInventory,
}: SalesDetailDrawerProps) {
  const t = useTranslations('sales');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const {
    getStageLabel,
    getNextActionLabel,
    getPriorityLabel,
    getPartyTypeLabel,
    getLossReasonLabel,
  } = useSalesLabels();

  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [timeline, setTimeline] = useState<OpportunityTimelineEntry[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [partyLead, setPartyLead] = useState<Lead | null>(null);
  const [partyInvestor, setPartyInvestor] = useState<Investor | null>(null);
  const [inventoryAssets, setInventoryAssets] = useState<InventoryAsset[]>([]);
  const [reservation, setReservation] = useState<InventoryReservation | null>(null);

  const canViewDocuments = user ? hasPermission(user, 'documents', 'view') : false;
  const canViewActivity = user ? hasPermission(user, 'activity', 'view') : false;
  const canViewFinance = user ? hasPermission(user, 'finance', 'view') : false;

  const loadTimeline = useCallback(async () => {
    if (!opportunity) return;
    setTimelineLoading(true);
    try {
      setTimeline(await fetchOpportunityTimeline(opportunity.id));
    } catch {
      setTimeline([]);
    } finally {
      setTimelineLoading(false);
    }
  }, [opportunity]);

  useEffect(() => {
    if (!opportunity) return;
    let cancelled = false;
    void (async () => {
      try {
        if (opportunity.party_type === 'lead') {
          const lead = await fetchLead(opportunity.party_id);
          if (!cancelled) setPartyLead(lead);
        } else {
          const investor = await fetchInvestor(opportunity.party_id);
          if (!cancelled) setPartyInvestor(investor);
        }
      } catch {
        if (!cancelled) {
          setPartyLead(null);
          setPartyInvestor(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [opportunity]);

  useEffect(() => {
    if (!linkedInventoryIds.length) {
      setInventoryAssets([]);
      return;
    }
    let cancelled = false;
    void Promise.all(linkedInventoryIds.map((id) => fetchInventoryAsset(id)))
      .then((assets) => {
        if (!cancelled) setInventoryAssets(assets);
      })
      .catch(() => {
        if (!cancelled) setInventoryAssets([]);
      });
    return () => {
      cancelled = true;
    };
  }, [linkedInventoryIds]);

  useEffect(() => {
    if (!opportunity?.reservation_id) {
      setReservation(null);
      return;
    }
    let cancelled = false;
    void fetchReservation(opportunity.reservation_id)
      .then((row) => {
        if (!cancelled) setReservation(row);
      })
      .catch(() => {
        if (!cancelled) setReservation(null);
      });
    return () => {
      cancelled = true;
    };
  }, [opportunity?.reservation_id]);

  useEffect(() => {
    if (opportunity && (activeTab === 'timeline' || activeTab === 'stageHistory')) {
      void loadTimeline();
    }
  }, [opportunity, activeTab, loadTimeline]);

  const linkedProjects = useMemo(
    () => projects.filter((p) => linkedProjectIds.includes(p.id)),
    [linkedProjectIds, projects],
  );

  if (!opportunity) return null;

  const tabs = [
    { id: 'overview', label: t('detail.tabs.overview') },
    { id: 'party', label: t('detail.tabs.party') },
    { id: 'projects', label: t('detail.tabs.projects') },
    { id: 'inventory', label: t('detail.tabs.inventory') },
    { id: 'stageHistory', label: t('detail.tabs.stageHistory') },
    { id: 'nextActions', label: t('detail.tabs.nextActions') },
    { id: 'reservations', label: t('detail.tabs.reservations') },
    ...(canViewDocuments ? [{ id: 'documents', label: t('detail.tabs.documents') }] : []),
    ...(canViewFinance ? [{ id: 'finance', label: t('detail.tabs.finance') }] : []),
    ...(canViewActivity ? [{ id: 'activity', label: t('detail.tabs.activity') }] : []),
    { id: 'timeline', label: t('detail.tabs.timeline') },
  ];

  const revenueDisplay =
    canViewSensitiveValue && opportunity.expected_revenue
      ? formatMoney(opportunity.expected_revenue, opportunity.currency, locale)
      : tCommon('noValue');

  return (
    <Drawer
      open
      onClose={onClose}
      wide
      title={opportunity.display_id ?? opportunity.opportunity_code}
      ariaLabel={t('detail.ariaLabel')}
      footer={
        <div className="sales__drawer-actions">
          {canUpdate && (
            <Button variant="secondary" onClick={() => onEdit(opportunity)}>
              {tCommon('edit')}
            </Button>
          )}
          {canChangeStage && (
            <Button variant="secondary" onClick={() => onChangeStage(opportunity)}>
              {t('detail.changeStage')}
            </Button>
          )}
          {canUpdate && (
            <Button variant="secondary" onClick={() => onEditNextAction(opportunity)}>
              {t('detail.editNextAction')}
            </Button>
          )}
          {canArchive && !opportunity.archived_at && (
            <Button variant="danger" disabled={archiving} onClick={() => onArchive(opportunity)}>
              {t('detail.archive')}
            </Button>
          )}
          {canRestore && opportunity.archived_at && (
            <Button variant="secondary" disabled={archiving} onClick={() => onRestore(opportunity)}>
              {t('detail.restore')}
            </Button>
          )}
        </div>
      }
    >
      <div className="sales__drawer-header-meta">
        <StatusChip tone="default">{getStageLabel(opportunity.stage)}</StatusChip>
        <span>{partyName ?? tCommon('noValue')}</span>
      </div>

      <Tabs
        tabs={tabs}
        activeId={activeTab}
        onChange={(id) => setActiveTab(id as DetailTab)}
        ariaLabel={t('detail.ariaLabel')}
      />

      <div className="leads-drawer__body">
        {activeTab === 'overview' && (
          <dl className="leads-drawer__grid">
            <DetailField label={t('table.party')} value={partyName ?? tCommon('noValue')} />
            <DetailField label={t('table.stage')} value={getStageLabel(opportunity.stage)} />
            <DetailField label={t('table.assignee')} value={assigneeName ?? tCommon('noValue')} />
            <DetailField label={t('table.value')} value={revenueDisplay} />
            <DetailField label={t('table.probability')} value={`${opportunity.probability}%`} />
            <DetailField label={t('table.priority')} value={getPriorityLabel(opportunity.priority)} />
            <DetailField
              label={t('table.expectedClose')}
              value={formatShortDate(opportunity.expected_close_date, locale)}
            />
            <DetailField label={t('form.source')} value={opportunity.source ?? tCommon('noValue')} />
            <DetailField label={t('form.notes')} value={opportunity.notes ?? tCommon('noValue')} />
          </dl>
        )}

        {activeTab === 'party' && (
          <section className="leads-drawer__section">
            <p>{getPartyTypeLabel(opportunity.party_type)}</p>
            {partyLead && (
              <dl className="leads-drawer__grid">
                <DetailField label={t('party.name')} value={partyLead.full_name} />
                <DetailField label={t('party.email')} value={partyLead.email ?? tCommon('noValue')} />
                <DetailField label={t('party.phone')} value={partyLead.phone ?? tCommon('noValue')} />
                <DetailField label={t('party.country')} value={partyLead.country ?? tCommon('noValue')} />
              </dl>
            )}
            {partyInvestor && (
              <dl className="leads-drawer__grid">
                <DetailField label={t('party.name')} value={partyInvestor.full_name} />
                <DetailField label={t('party.email')} value={partyInvestor.email ?? tCommon('noValue')} />
                <DetailField label={t('party.phone')} value={partyInvestor.phone ?? tCommon('noValue')} />
              </dl>
            )}
            {!partyLead && !partyInvestor && <p className="leads__state">{t('party.loadError')}</p>}
          </section>
        )}

        {activeTab === 'projects' && (
          <section className="leads-drawer__section">
            {canUpdate && (
              <Button variant="secondary" onClick={() => onLinkProject(opportunity)}>
                {t('detail.linkProject')}
              </Button>
            )}
            {linkedProjects.length === 0 ? (
              <p className="leads__state">{t('detail.noProjects')}</p>
            ) : (
              <ul className="sales__linked-list">
                {linkedProjects.map((project) => (
                  <li key={project.id}>
                    <Link href={`/dashboard/projects?id=${project.id}`}>{project.project_name}</Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {activeTab === 'inventory' && (
          <section className="leads-drawer__section">
            {canUpdate && (
              <Button variant="secondary" onClick={() => onLinkInventory(opportunity)}>
                {t('detail.linkInventory')}
              </Button>
            )}
            {inventoryAssets.length === 0 ? (
              <p className="leads__state">{t('detail.noInventory')}</p>
            ) : (
              <ul className="sales__linked-list">
                {inventoryAssets.map((asset) => (
                  <li key={asset.id}>
                    <Link href={`/dashboard/inventory?id=${asset.id}`}>
                      {asset.display_id ?? asset.system_code}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {activeTab === 'stageHistory' && (
          <section className="leads-drawer__section">
            {timelineLoading && <p className="leads__state">{tCommon('loading')}</p>}
            {!timelineLoading && timeline.length === 0 && (
              <p className="leads__state">{t('detail.noTimeline')}</p>
            )}
            <ul className="activity-timeline__list">
              {timeline
                .filter((entry) => entry.from_stage || entry.to_stage)
                .map((entry) => (
                  <li key={entry.id}>
                    <strong>
                      {entry.from_stage ? getStageLabel(entry.from_stage) : '—'} →{' '}
                      {entry.to_stage ? getStageLabel(entry.to_stage) : '—'}
                    </strong>
                    <span>{formatShortDate(entry.created_at, locale)}</span>
                    {entry.notes && <p>{entry.notes}</p>}
                  </li>
                ))}
            </ul>
          </section>
        )}

        {activeTab === 'nextActions' && (
          <section className="leads-drawer__section">
            <dl className="leads-drawer__grid">
              <DetailField
                label={t('nextAction.action')}
                value={
                  opportunity.next_action
                    ? getNextActionLabel(opportunity.next_action)
                    : tCommon('noValue')
                }
              />
              <DetailField
                label={t('nextAction.date')}
                value={formatShortDate(opportunity.next_action_date, locale)}
              />
            </dl>
            {canUpdate && (
              <Button variant="secondary" onClick={() => onEditNextAction(opportunity)}>
                {t('detail.editNextAction')}
              </Button>
            )}
          </section>
        )}

        {activeTab === 'reservations' && (
          <section className="leads-drawer__section">
            {!reservation ? (
              <p className="leads__state">{t('detail.noReservation')}</p>
            ) : (
              <dl className="leads-drawer__grid">
                <DetailField label={t('reservation.status')} value={reservation.status} />
                <DetailField label={t('reservation.type')} value={reservation.reservation_type} />
                <DetailField
                  label={t('reservation.deposit')}
                  value={
                    reservation.deposit_amount
                      ? formatMoney(reservation.deposit_amount, reservation.deposit_currency ?? 'USD', locale)
                      : tCommon('noValue')
                  }
                />
              </dl>
            )}
          </section>
        )}

        {activeTab === 'documents' && canViewDocuments && (
          <EntityDocumentsPanel
            entityType="lead"
            entityId={opportunity.lead_id ?? opportunity.party_id}
            leadId={opportunity.lead_id ?? undefined}
          />
        )}

        {activeTab === 'finance' && canViewFinance && (
          <section className="leads-drawer__section">
            <p className="leads__state">{t('detail.financePlaceholder')}</p>
            {opportunity.expected_revenue && canViewSensitiveValue && (
              <p>
                {t('detail.expectedRevenue')}: {revenueDisplay}
              </p>
            )}
            {opportunity.loss_reason && (
              <p>
                {t('stageChange.lossReason')}: {getLossReasonLabel(opportunity.loss_reason)}
              </p>
            )}
          </section>
        )}

        {activeTab === 'activity' && canViewActivity && opportunity.lead_id && (
          <EntityActivityTimeline entityType="lead" entityId={opportunity.lead_id} />
        )}

        {activeTab === 'timeline' && (
          <section className="leads-drawer__section">
            {timelineLoading && <p className="leads__state">{tCommon('loading')}</p>}
            {!timelineLoading && timeline.length === 0 && (
              <p className="leads__state">{t('detail.noTimeline')}</p>
            )}
            <ul className="activity-timeline__list">
              {timeline.map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.event_type}</strong>
                  <span>{formatShortDate(entry.created_at, locale)}</span>
                  {entry.notes && <p>{entry.notes}</p>}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </Drawer>
  );
}

