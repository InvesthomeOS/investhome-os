'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, StatusChip, Tabs } from '@investhome/ui';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import { hasPermission } from '@/lib/api/auth';
import {
  fetchLeadInventoryInterests,
  fetchLeadDetailSummary,
  fetchLeadFollowUps,
  fetchLeadQualification,
  fetchLeadScore,
  fetchLeadTimeline,
  updateLeadQualification,
  changeQualificationStatus,
  recalculateLeadScore,
  createLeadFollowUp,
  completeLeadFollowUp,
  deleteLeadInventoryInterest,
  type LeadQualification,
  type LeadScore,
  type LeadFollowUp,
  type LeadInventoryInterest,
  type LeadTimelineEntry,
  type LeadDetailSummary,
  type QualificationStatus,
} from '@/lib/api/lead-qualification';
import { fetchLead, formatBudget, formatDate, type Lead } from '@/lib/api/leads';
import { fetchReservations, type InventoryReservation } from '@/lib/api/inventory';
import { fetchOpportunities, type SalesOpportunity } from '@/lib/api/sales';
import { useAuth } from '@/lib/auth/auth-context';
import { useLeadLabels } from '@/lib/i18n/lead-labels';
import { useLeadQualificationLabels } from '@/lib/i18n/lead-qualification-labels';

type DetailTab =
  | 'overview'
  | 'contact'
  | 'qualification'
  | 'opportunities'
  | 'inventory'
  | 'followUps'
  | 'reservations'
  | 'documents'
  | 'activity'
  | 'timeline';

interface LeadDetailPageProps {
  leadId: string;
}

function DetailField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function LeadDetailPage({ leadId }: LeadDetailPageProps) {
  const t = useTranslations('leadQualification');
  const tLeads = useTranslations('leads');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getStatusLabel, getSourceLabel } = useLeadLabels();
  const {
    getQualificationStatusLabel,
    getFollowUpTypeLabel,
    getScoreComponentLabel,
    getInterestTypeLabel,
    qualificationStatusOptions,
    investmentObjectiveOptions,
    cashOrFinancingOptions,
    timelineOptions,
    riskToleranceOptions,
  } = useLeadQualificationLabels();

  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [lead, setLead] = useState<Lead | null>(null);
  const [summary, setSummary] = useState<LeadDetailSummary | null>(null);
  const [qualification, setQualification] = useState<LeadQualification | null>(null);
  const [score, setScore] = useState<LeadScore | null>(null);
  const [opportunities, setOpportunities] = useState<SalesOpportunity[]>([]);
  const [interests, setInterests] = useState<LeadInventoryInterest[]>([]);
  const [followUps, setFollowUps] = useState<LeadFollowUp[]>([]);
  const [reservations, setReservations] = useState<InventoryReservation[]>([]);
  const [timeline, setTimeline] = useState<LeadTimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canViewLead = user ? hasPermission(user, 'sales', 'view_lead') || hasPermission(user, 'leads', 'view') : false;
  const canQualify = user ? hasPermission(user, 'sales', 'qualify_lead') : false;
  const canScore = user ? hasPermission(user, 'sales', 'score_lead') : false;
  const canUpdate = user ? hasPermission(user, 'sales', 'update_lead') || hasPermission(user, 'leads', 'update') : false;
  const canViewDocuments = user ? hasPermission(user, 'documents', 'view') : false;
  const canViewActivity = user ? hasPermission(user, 'activity', 'view') : false;
  const canViewReservations = user ? hasPermission(user, 'sales', 'view_reservations') || hasPermission(user, 'inventory', 'view') : false;
  const canCreateOpportunity = user ? hasPermission(user, 'sales', 'create_opportunity') || hasPermission(user, 'sales', 'create') : false;

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [leadData, summaryData, qualData, scoreData, opps, interestData, followUpData, timelineData] =
        await Promise.all([
          fetchLead(leadId),
          fetchLeadDetailSummary(leadId),
          fetchLeadQualification(leadId),
          fetchLeadScore(leadId),
          fetchOpportunities({ lead_id: leadId, limit: 50 }),
          fetchLeadInventoryInterests(leadId),
          fetchLeadFollowUps(leadId),
          fetchLeadTimeline(leadId),
        ]);
      setLead(leadData);
      setSummary(summaryData);
      setQualification(qualData);
      setScore(scoreData);
      setOpportunities(opps.items);
      setInterests(interestData);
      setFollowUps(followUpData);
      setTimeline(timelineData);
      if (canViewReservations) {
        const resv = await fetchReservations({ lead_id: leadId });
        setReservations(resv.items);
      }
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [leadId, t, canViewReservations]);

  useEffect(() => {
    if (canViewLead) void loadAll();
  }, [canViewLead, loadAll]);

  const tabs = useMemo(
    () =>
      [
        { id: 'overview' as const, label: t('tabs.overview') },
        { id: 'contact' as const, label: t('tabs.contact') },
        { id: 'qualification' as const, label: t('tabs.qualification') },
        { id: 'opportunities' as const, label: t('tabs.opportunities') },
        { id: 'inventory' as const, label: t('tabs.inventory') },
        { id: 'followUps' as const, label: t('tabs.followUps') },
        { id: 'reservations' as const, label: t('tabs.reservations') },
        { id: 'documents' as const, label: t('tabs.documents'), hidden: !canViewDocuments },
        { id: 'activity' as const, label: t('tabs.activity'), hidden: !canViewActivity },
        { id: 'timeline' as const, label: t('tabs.timeline') },
      ].filter((tab) => !tab.hidden),
    [t, canViewDocuments, canViewActivity],
  );

  const handleQualificationSave = async (updates: Partial<LeadQualification>) => {
    if (!canQualify) return;
    setSaving(true);
    setActionError(null);
    try {
      const updated = await updateLeadQualification(leadId, updates);
      setQualification(updated);
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (status: QualificationStatus) => {
    if (!canQualify) return;
    setSaving(true);
    try {
      const updated = await changeQualificationStatus(leadId, status);
      setQualification(updated);
      await loadAll();
    } catch {
      setActionError(t('statusError'));
    } finally {
      setSaving(false);
    }
  };

  const handleRecalculateScore = async () => {
    if (!canScore) return;
    setSaving(true);
    try {
      const updated = await recalculateLeadScore(leadId);
      setScore(updated);
      await loadAll();
    } catch {
      setActionError(t('scoreError'));
    } finally {
      setSaving(false);
    }
  };

  const handleCreateFollowUp = async () => {
    if (!canUpdate) return;
    const dueAt = new Date(Date.now() + 86400000).toISOString();
    setSaving(true);
    try {
      await createLeadFollowUp(leadId, { follow_up_type: 'call', due_at: dueAt });
      setFollowUps(await fetchLeadFollowUps(leadId));
    } catch {
      setActionError(t('followUpError'));
    } finally {
      setSaving(false);
    }
  };

  const handleCompleteFollowUp = async (followUpId: string) => {
    if (!canUpdate) return;
    setSaving(true);
    try {
      await completeLeadFollowUp(leadId, followUpId);
      setFollowUps(await fetchLeadFollowUps(leadId));
    } catch {
      setActionError(t('followUpError'));
    } finally {
      setSaving(false);
    }
  };

  if (!canViewLead) {
    return (
      <div className="leads__state leads__state--error">
        <p>{t('noAccess')}</p>
      </div>
    );
  }

  if (loading) {
    return <p className="leads__state">{tCommon('loading')}</p>;
  }

  if (error || !lead) {
    return (
      <div className="leads__state leads__state--error">
        <p>{error ?? t('loadError')}</p>
        <Link href="/dashboard/leads" className="leads__button leads__button--secondary">
          {t('backToList')}
        </Link>
      </div>
    );
  }

  return (
    <div className="dashboard__content">
      <header className="dashboard__header leads__header">
        <div>
          <p className="dashboard__eyebrow">{tLeads('detailEyebrow')}</p>
          <h1>{lead.full_name}</h1>
          {lead.is_demo && <span className="leads__demo-tag">{tCommon('demoData')}</span>}
        </div>
        <div className="leads__filter-actions">
          <Link href="/dashboard/leads" className="leads__button leads__button--ghost">
            {t('backToList')}
          </Link>
          {lead.phone && (
            <a href={`tel:${lead.phone}`} className="leads__button leads__button--secondary">
              {t('actions.call')}
            </a>
          )}
          {lead.email && (
            <a href={`mailto:${lead.email}`} className="leads__button leads__button--secondary">
              {t('actions.email')}
            </a>
          )}
          {lead.phone && (
            <a
              href={`https://wa.me/${lead.phone.replace(/\D/g, '')}`}
              target="_blank"
              rel="noreferrer"
              className="leads__button leads__button--secondary"
            >
              {t('actions.whatsapp')}
            </a>
          )}
          {canUpdate && (
            <Button variant="secondary" onClick={() => void handleCreateFollowUp()} disabled={saving}>
              {t('actions.scheduleFollowUp')}
            </Button>
          )}
          {canCreateOpportunity && (
            <Link href={`/dashboard/sales?lead_id=${leadId}`} className="leads__button leads__button--primary">
              {t('actions.createOpportunity')}
            </Link>
          )}
        </div>
      </header>

      {actionError && <p className="leads__error">{actionError}</p>}

      <section className="dashboard__panel leads__panel">
        <Tabs
          tabs={tabs.map(({ id, label }) => ({ id, label }))}
          activeId={activeTab}
          onChange={(id) => setActiveTab(id as DetailTab)}
          ariaLabel={t('tabs.overview')}
        />

        <div className="leads-drawer__body" style={{ marginTop: '1rem' }}>
          {activeTab === 'overview' && (
            <dl className="leads-drawer__grid">
              <DetailField label={tLeads('detail.status')} value={getStatusLabel(lead.status)} />
              <DetailField
                label={t('overview.qualificationStatus')}
                value={
                  qualification ? (
                    <StatusChip tone="info">{getQualificationStatusLabel(qualification.qualification_status)}</StatusChip>
                  ) : (
                    '—'
                  )
                }
              />
              <DetailField label={t('overview.leadScore')} value={score?.total_score ?? summary?.lead_score ?? '—'} />
              <DetailField label={tLeads('detail.source')} value={getSourceLabel(lead.source)} />
              <DetailField label={tLeads('detail.assignedTo')} value={lead.assigned_to ?? tCommon('noValue')} />
              <DetailField label={tLeads('detail.budget')} value={formatBudget(lead.estimated_budget, locale)} />
              <DetailField label={tLeads('detail.project')} value={lead.interested_project ?? tCommon('noValue')} />
              <DetailField label={t('overview.company')} value={lead.company ?? tCommon('noValue')} />
              <DetailField label={t('overview.preferredMarket')} value={lead.preferred_market ?? tCommon('noValue')} />
              <DetailField label={t('overview.opportunities')} value={summary?.opportunity_count ?? 0} />
              <DetailField label={t('overview.reservations')} value={summary?.reservation_count ?? 0} />
              <DetailField label={t('overview.inventoryMatches')} value={summary?.inventory_interest_count ?? 0} />
              <DetailField label={t('overview.pendingFollowUps')} value={summary?.pending_follow_up_count ?? 0} />
              <DetailField label={tLeads('detail.created')} value={formatDate(lead.created_at, locale)} />
              <DetailField label={tLeads('detail.updated')} value={formatDate(lead.updated_at, locale)} />
            </dl>
          )}

          {activeTab === 'contact' && (
            <dl className="leads-drawer__grid">
              <DetailField label={tLeads('detail.email')} value={lead.email ?? tCommon('noValue')} />
              <DetailField label={tLeads('detail.phone')} value={lead.phone ?? tCommon('noValue')} />
              <DetailField label={tLeads('detail.country')} value={lead.country ?? tCommon('noValue')} />
              <DetailField label={t('overview.company')} value={lead.company ?? tCommon('noValue')} />
              <DetailField label={tLeads('detail.notes')} value={lead.notes ?? tLeads('noNotes')} />
            </dl>
          )}

          {activeTab === 'qualification' && qualification && (
            <div className="leads-form leads-form--grid">
              <label className="leads__field">
                <span>{t('fields.investmentObjective')}</span>
                <select
                  value={qualification.investment_objective ?? ''}
                  disabled={!canQualify || saving}
                  onChange={(e) =>
                    void handleQualificationSave({
                      investment_objective: (e.target.value || null) as LeadQualification['investment_objective'],
                    })
                  }
                >
                  <option value="">{tCommon('noValue')}</option>
                  {investmentObjectiveOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('fields.budgetMin')}</span>
                <input
                  type="number"
                  defaultValue={qualification.budget_min ?? ''}
                  disabled={!canQualify || saving}
                  onBlur={(e) =>
                    void handleQualificationSave({ budget_min: e.target.value || null })
                  }
                />
              </label>
              <label className="leads__field">
                <span>{t('fields.budgetMax')}</span>
                <input
                  type="number"
                  defaultValue={qualification.budget_max ?? ''}
                  disabled={!canQualify || saving}
                  onBlur={(e) =>
                    void handleQualificationSave({ budget_max: e.target.value || null })
                  }
                />
              </label>
              <label className="leads__field">
                <span>{t('fields.timeline')}</span>
                <select
                  value={qualification.expected_purchase_timeline ?? ''}
                  disabled={!canQualify || saving}
                  onChange={(e) =>
                    void handleQualificationSave({
                      expected_purchase_timeline: (e.target.value || null) as LeadQualification['expected_purchase_timeline'],
                    })
                  }
                >
                  <option value="">{tCommon('noValue')}</option>
                  {timelineOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('fields.financing')}</span>
                <select
                  value={qualification.cash_or_financing ?? ''}
                  disabled={!canQualify || saving}
                  onChange={(e) =>
                    void handleQualificationSave({
                      cash_or_financing: (e.target.value || null) as LeadQualification['cash_or_financing'],
                    })
                  }
                >
                  <option value="">{tCommon('noValue')}</option>
                  {cashOrFinancingOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field">
                <span>{t('fields.riskTolerance')}</span>
                <select
                  value={qualification.risk_tolerance ?? ''}
                  disabled={!canQualify || saving}
                  onChange={(e) =>
                    void handleQualificationSave({
                      risk_tolerance: (e.target.value || null) as LeadQualification['risk_tolerance'],
                    })
                  }
                >
                  <option value="">{tCommon('noValue')}</option>
                  {riskToleranceOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leads__field leads__field--full">
                <span>{t('fields.salesNotes')}</span>
                <textarea
                  defaultValue={qualification.sales_notes ?? ''}
                  disabled={!canQualify || saving}
                  onBlur={(e) => void handleQualificationSave({ sales_notes: e.target.value || null })}
                />
              </label>
              <div className="leads__field leads__field--full">
                <span>{t('fields.qualificationStatus')}</span>
                <div className="leads__filter-actions">
                  {qualificationStatusOptions.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`leads__button${qualification.qualification_status === opt.value ? ' leads__button--primary' : ' leads__button--secondary'}`}
                      disabled={!canQualify || saving}
                      onClick={() => void handleStatusChange(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
              {canScore && (
                <div className="leads__field leads__field--full">
                  <span>{t('overview.leadScore')}: {score?.total_score ?? '—'}</span>
                  <Button variant="secondary" onClick={() => void handleRecalculateScore()} disabled={saving}>
                    {t('actions.recalculateScore')}
                  </Button>
                  {score?.components && (
                    <ul>
                      {score.components.map((c) => (
                        <li key={c.component_key}>
                          {getScoreComponentLabel(c.component_key)}: {c.score}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'opportunities' && (
            <section>
              {opportunities.length === 0 ? (
                <p className="leads__state">{t('opportunities.empty')}</p>
              ) : (
                <ul>
                  {opportunities.map((opp) => (
                    <li key={opp.id}>
                      <Link href={`/dashboard/sales?id=${opp.id}`}>{opp.opportunity_code}</Link>
                      {' — '}
                      {opp.stage}
                    </li>
                  ))}
                </ul>
              )}
              {canCreateOpportunity && (
                <Link href={`/dashboard/sales?lead_id=${leadId}`} className="leads__button leads__button--primary">
                  {t('actions.createOpportunity')}
                </Link>
              )}
            </section>
          )}

          {activeTab === 'inventory' && (
            <section>
              {interests.length === 0 ? (
                <p className="leads__state">{t('inventory.empty')}</p>
              ) : (
                <ul>
                  {interests.map((item) => (
                    <li key={item.id}>
                      <Link href={`/dashboard/inventory?id=${item.inventory_asset_id}`}>
                        {item.inventory_asset_id.slice(0, 8)}…
                      </Link>
                      {' — '}
                      {getInterestTypeLabel(item.interest_type)}
                      {canUpdate && (
                        <button
                          type="button"
                          className="leads__button leads__button--ghost"
                          onClick={() => void deleteLeadInventoryInterest(leadId, item.id).then(loadAll)}
                        >
                          {t('actions.removeMatch')}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {activeTab === 'followUps' && (
            <section>
              <p className="leads__state">{t('followUps.calendarNote')}</p>
              {followUps.length === 0 ? (
                <p className="leads__state">{t('followUps.empty')}</p>
              ) : (
                <ul>
                  {followUps.map((fu) => (
                    <li key={fu.id}>
                      {getFollowUpTypeLabel(fu.follow_up_type)} — {formatDate(fu.due_at, locale)} — {fu.status}
                      {fu.status === 'pending' && canUpdate && (
                        <button
                          type="button"
                          className="leads__button leads__button--ghost"
                          onClick={() => void handleCompleteFollowUp(fu.id)}
                        >
                          {t('followUps.complete')}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {canUpdate && (
                <Button variant="secondary" onClick={() => void handleCreateFollowUp()} disabled={saving}>
                  {t('actions.scheduleFollowUp')}
                </Button>
              )}
            </section>
          )}

          {activeTab === 'reservations' && (
            <section>
              {!canViewReservations ? (
                <p className="leads__state">{t('noAccess')}</p>
              ) : reservations.length === 0 ? (
                <p className="leads__state">{t('reservations.empty')}</p>
              ) : (
                <ul>
                  {reservations.map((r) => (
                    <li key={r.id}>
                      {r.id.slice(0, 8)} — {r.status}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {activeTab === 'documents' && canViewDocuments && (
            <EntityDocumentsPanel entityType="lead" entityId={leadId} leadId={leadId} />
          )}

          {activeTab === 'activity' && canViewActivity && (
            <EntityActivityTimeline entityType="lead" entityId={leadId} />
          )}

          {activeTab === 'timeline' && (
            <section>
              {timeline.length === 0 ? (
                <p className="leads__state">{t('timeline.empty')}</p>
              ) : (
                <ul>
                  {timeline.map((entry, idx) => (
                    <li key={`${entry.created_at}-${idx}`}>
                      <strong>{entry.event_type}</strong> — {formatDate(entry.created_at, locale)}
                      {entry.notes && <span> — {entry.notes}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      </section>
    </div>
  );
}
