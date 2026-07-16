'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchLead, type Lead } from '@/lib/api/leads';
import { fetchInvestor, type Investor } from '@/lib/api/investors';
import {
  OPPORTUNITY_NEXT_ACTIONS,
  OPPORTUNITY_PRIORITIES,
  type OpportunityNextAction,
  type OpportunityPartyType,
  type OpportunityPriority,
  type OpportunityStage,
  type SalesOpportunityInput,
} from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

interface SalesFormModalProps {
  mode: 'create' | 'edit';
  initialLeadId?: string | null;
  initialPartyId?: string | null;
  initialPartyType?: OpportunityPartyType;
  initialValues?: Partial<SalesOpportunityInput>;
  users: { id: string; full_name: string }[];
  submitting: boolean;
  onClose: () => void;
  onSubmit: (input: SalesOpportunityInput) => void;
}

export function SalesFormModal({
  mode,
  initialLeadId,
  initialPartyId,
  initialPartyType = 'lead',
  initialValues,
  users,
  submitting,
  onClose,
  onSubmit,
}: SalesFormModalProps) {
  const t = useTranslations('sales');
  const tCommon = useTranslations('common');
  const { getStageLabel, getNextActionLabel, getPriorityLabel, partyTypeOptions } = useSalesLabels();

  const [partyId, setPartyId] = useState(initialPartyId ?? '');
  const [partyType, setPartyType] = useState<OpportunityPartyType>(initialPartyType);
  const [leadId, setLeadId] = useState(initialLeadId ?? '');
  const [assignedUserId, setAssignedUserId] = useState(initialValues?.assigned_sales_user_id ?? '');
  const [stage, setStage] = useState<OpportunityStage>(initialValues?.stage ?? 'new');
  const [probability, setProbability] = useState(String(initialValues?.probability ?? 0));
  const [expectedCloseDate, setExpectedCloseDate] = useState(initialValues?.expected_close_date ?? '');
  const [expectedRevenue, setExpectedRevenue] = useState(
    initialValues?.expected_revenue != null ? String(initialValues.expected_revenue) : '',
  );
  const [currency, setCurrency] = useState(initialValues?.currency ?? 'USD');
  const [priority, setPriority] = useState<OpportunityPriority>(initialValues?.priority ?? 'medium');
  const [source, setSource] = useState(initialValues?.source ?? '');
  const [nextAction, setNextAction] = useState<OpportunityNextAction | ''>(
    initialValues?.next_action ?? '',
  );
  const [nextActionDate, setNextActionDate] = useState(initialValues?.next_action_date ?? '');
  const [notes, setNotes] = useState(initialValues?.notes ?? '');
  const [partyPreview, setPartyPreview] = useState<string>('');

  useEffect(() => {
    if (!partyId) {
      setPartyPreview('');
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        if (partyType === 'lead') {
          const lead: Lead = await fetchLead(partyId);
          if (!cancelled) setPartyPreview(lead.full_name);
        } else {
          const investor: Investor = await fetchInvestor(partyId);
          if (!cancelled) setPartyPreview(investor.full_name);
        }
      } catch {
        if (!cancelled) setPartyPreview('');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [partyId, partyType]);

  useEffect(() => {
    if (initialLeadId) {
      setLeadId(initialLeadId);
      setPartyId(initialPartyId ?? initialLeadId);
      setPartyType('lead');
    }
  }, [initialLeadId, initialPartyId]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!partyId.trim()) return;
    onSubmit({
      party_id: partyId.trim(),
      party_type: partyType,
      lead_id: leadId.trim() || null,
      assigned_sales_user_id: assignedUserId || null,
      ...(mode === 'create' ? { stage } : {}),
      probability: Number(probability),
      expected_close_date: expectedCloseDate || null,
      expected_revenue: expectedRevenue ? Number(expectedRevenue) : null,
      currency,
      priority,
      source: source.trim() || null,
      next_action: nextAction || null,
      next_action_date: nextActionDate || null,
      notes: notes.trim() || null,
    });
  };

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <form
        className="leads-modal__panel leads-modal__panel--wide"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <header className="leads-modal__header">
          <h2>{mode === 'create' ? t('form.createTitle') : t('form.editTitle')}</h2>
        </header>
        <div className="leads-form leads-form--grid">
          <label className="leads__field">
            <span>{t('form.partyType')}</span>
            <select
              value={partyType}
              onChange={(e) => setPartyType(e.target.value as OpportunityPartyType)}
              disabled={mode === 'edit'}
            >
              {partyTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="leads__field">
            <span>{t('form.partyId')}</span>
            <input
              type="text"
              value={partyId}
              onChange={(e) => setPartyId(e.target.value)}
              required
              disabled={mode === 'edit'}
            />
            {partyPreview && <small>{partyPreview}</small>}
          </label>
          <label className="leads__field">
            <span>{t('form.leadId')}</span>
            <input type="text" value={leadId} onChange={(e) => setLeadId(e.target.value)} />
          </label>
          <label className="leads__field">
            <span>{t('form.assignee')}</span>
            <select value={assignedUserId} onChange={(e) => setAssignedUserId(e.target.value)}>
              <option value="">{t('form.unassigned')}</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name}
                </option>
              ))}
            </select>
          </label>
          {mode === 'create' && (
            <label className="leads__field">
              <span>{t('form.stage')}</span>
              <select value={stage} onChange={(e) => setStage(e.target.value as OpportunityStage)}>
                {['new', 'qualified'].map((value) => (
                  <option key={value} value={value}>
                    {getStageLabel(value)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="leads__field">
            <span>{t('form.probability')}</span>
            <input
              type="number"
              min={0}
              max={100}
              value={probability}
              onChange={(e) => setProbability(e.target.value)}
            />
          </label>
          <label className="leads__field">
            <span>{t('form.expectedRevenue')}</span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={expectedRevenue}
              onChange={(e) => setExpectedRevenue(e.target.value)}
            />
          </label>
          <label className="leads__field">
            <span>{t('form.currency')}</span>
            <input type="text" maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} />
          </label>
          <label className="leads__field">
            <span>{t('form.priority')}</span>
            <select value={priority} onChange={(e) => setPriority(e.target.value as OpportunityPriority)}>
              {OPPORTUNITY_PRIORITIES.map((value) => (
                <option key={value} value={value}>
                  {getPriorityLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="leads__field">
            <span>{t('form.expectedCloseDate')}</span>
            <input type="date" value={expectedCloseDate} onChange={(e) => setExpectedCloseDate(e.target.value)} />
          </label>
          <label className="leads__field">
            <span>{t('form.source')}</span>
            <input type="text" value={source} onChange={(e) => setSource(e.target.value)} />
          </label>
          <label className="leads__field">
            <span>{t('form.nextAction')}</span>
            <select value={nextAction} onChange={(e) => setNextAction(e.target.value as OpportunityNextAction | '')}>
              <option value="">{tCommon('noValue')}</option>
              {OPPORTUNITY_NEXT_ACTIONS.map((action) => (
                <option key={action} value={action}>
                  {getNextActionLabel(action)}
                </option>
              ))}
            </select>
          </label>
          <label className="leads__field">
            <span>{t('form.nextActionDate')}</span>
            <input type="date" value={nextActionDate} onChange={(e) => setNextActionDate(e.target.value)} />
          </label>
          <label className="leads__field leads__field--full">
            <span>{t('form.notes')}</span>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
          </label>
        </div>
        <footer className="leads-modal__footer">
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            {tCommon('cancel')}
          </button>
          <button type="submit" className="leads__button leads__button--primary" disabled={submitting}>
            {mode === 'create' ? t('form.create') : t('form.save')}
          </button>
        </footer>
      </form>
    </div>
  );
}
