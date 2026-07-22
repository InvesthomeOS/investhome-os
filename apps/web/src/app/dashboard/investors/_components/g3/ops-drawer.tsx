'use client';

import { useEffect, useState } from 'react';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import {
  formatCurrency,
  formatDate,
  formatShortDate,
  type Investor,
} from '@/lib/api/investors';

import {
  appendStageHistory,
  getBoardMeta,
  setBoardMeta,
  type InvestorPriority,
} from './board-meta';
import {
  INVESTOR_LIFECYCLE_STAGES,
  stageProbability,
  toLifecycleStage,
  type InvestorLifecycleStage,
} from './lifecycle';

type DrawerTab =
  | 'overview'
  | 'profile'
  | 'stage'
  | 'activity'
  | 'documents'
  | 'notes'
  | 'ai';

interface OpsDrawerProps {
  investor: Investor | null;
  locale: string;
  canUpdate: boolean;
  archiving: boolean;
  saving: boolean;
  stageLabel: (stage: InvestorLifecycleStage) => string;
  typeLabel: (type: string) => string;
  statusLabel: (status: string) => string;
  modelLabel: (model: string | null) => string;
  accreditationLabel: (v: string) => string;
  riskLabel: (v: string | null) => string;
  priorityLabel: (p: InvestorPriority) => string;
  labels: Record<string, string>;
  onClose: () => void;
  onEdit: (investor: Investor) => void;
  onArchive: (investor: Investor) => void;
  onStageChange: (investor: Investor, stage: InvestorLifecycleStage, note?: string) => Promise<void>;
  onFieldPatch: (
    investor: Investor,
    patch: Partial<{
      assigned_to: string | null;
      next_follow_up_date: string | null;
      investment_capacity: number | null;
      notes: string | null;
      last_contact_date: string | null;
    }>,
  ) => Promise<void>;
  metaVersion: number;
  onMetaChange: () => void;
}

export function OpsDrawer({
  investor,
  locale,
  canUpdate,
  archiving,
  saving,
  stageLabel,
  typeLabel,
  statusLabel,
  modelLabel,
  accreditationLabel,
  riskLabel,
  priorityLabel,
  labels,
  onClose,
  onEdit,
  onArchive,
  onStageChange,
  onFieldPatch,
  metaVersion,
  onMetaChange,
}: OpsDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>('overview');
  const [stageNote, setStageNote] = useState('');
  const [nextStage, setNextStage] = useState<InvestorLifecycleStage>('new_investor');
  const [probability, setProbability] = useState('10');
  const [priority, setPriority] = useState<InvestorPriority>('medium');
  const [nextAction, setNextAction] = useState('');
  const [assigned, setAssigned] = useState('');
  const [closeDate, setCloseDate] = useState('');
  const [capacity, setCapacity] = useState('');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (!investor) return;
    const stage = toLifecycleStage(investor.status);
    const meta = getBoardMeta(investor.id);
    setTab('overview');
    setNextStage(stage);
    setProbability(String(meta.probability ?? stageProbability(stage)));
    setPriority(meta.priority ?? 'medium');
    setNextAction(meta.nextAction ?? '');
    setAssigned(investor.assigned_to ?? '');
    setCloseDate(investor.next_follow_up_date ?? '');
    setCapacity(investor.investment_capacity ?? '');
    setNotes(investor.notes ?? '');
    setStageNote('');
  }, [investor, metaVersion]);

  if (!investor) return null;

  const stage = toLifecycleStage(investor.status);
  const meta = getBoardMeta(investor.id);
  const tabs: { id: DrawerTab; label: string }[] = [
    { id: 'overview', label: labels.tabOverview ?? 'Overview' },
    { id: 'profile', label: labels.tabProfile ?? 'Profile' },
    { id: 'stage', label: labels.tabStage ?? 'Stage' },
    { id: 'notes', label: labels.tabNotes ?? 'Notes' },
    { id: 'activity', label: labels.tabActivity ?? 'Activity' },
    { id: 'documents', label: labels.tabDocuments ?? 'Documents' },
    { id: 'ai', label: labels.tabAi ?? 'AI' },
  ];

  const saveMetaLocal = () => {
    setBoardMeta(investor.id, {
      probability: Number(probability) || 0,
      priority,
      nextAction: nextAction || undefined,
    });
    onMetaChange();
  };

  return (
    <div className="inv-g3-drawer" role="presentation" onClick={onClose} data-testid="inv-g3-drawer">
      <aside
        className="inv-g3-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inv-g3-drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="inv-g3-drawer__header">
          <div>
            <p className="inv-g3__eyebrow">{labels.detailEyebrow}</p>
            <h2 id="inv-g3-drawer-title">{investor.full_name}</h2>
            <p className="inv-g3__subtitle">
              {stageLabel(stage)} · {typeLabel(investor.investor_type)}
              {investor.is_demo ? ` · ${labels.demo}` : ''}
            </p>
          </div>
          <button type="button" className="inv-g3__btn inv-g3__btn--ghost" onClick={onClose}>
            {labels.close}
          </button>
        </header>

        <div className="inv-g3-drawer__actions">
          <button
            type="button"
            className="inv-g3__btn"
            disabled={!canUpdate}
            onClick={() => onEdit(investor)}
          >
            {labels.edit}
          </button>
          <button
            type="button"
            className="inv-g3__btn inv-g3__btn--primary"
            disabled={!canUpdate || saving}
            onClick={async () => {
              saveMetaLocal();
              await onFieldPatch(investor, {
                assigned_to: assigned || null,
                next_follow_up_date: closeDate || null,
                investment_capacity: capacity ? Number(capacity) : null,
                notes: notes || null,
              });
            }}
          >
            {saving ? labels.saving : labels.save}
          </button>
          <button
            type="button"
            className="inv-g3__btn"
            disabled={!canUpdate || archiving}
            onClick={() => onArchive(investor)}
          >
            {archiving ? labels.archiving : labels.archive}
          </button>
        </div>

        <div className="inv-g3-drawer__tabs" role="tablist">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              className={`inv-g3-drawer__tab${tab === t.id ? ' is-active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="inv-g3-drawer__body">
          {tab === 'overview' ? (
            <>
              <dl className="inv-g3-drawer__grid">
                <div>
                  <dt>{labels.email}</dt>
                  <dd>{investor.email ?? '—'}</dd>
                </div>
                <div>
                  <dt>{labels.phone}</dt>
                  <dd>{investor.phone ?? '—'}</dd>
                </div>
                <div>
                  <dt>{labels.country}</dt>
                  <dd>{investor.country ?? '—'}</dd>
                </div>
                <div>
                  <dt>{labels.capacity}</dt>
                  <dd>{formatCurrency(investor.investment_capacity, locale)}</dd>
                </div>
                <div>
                  <dt>{labels.stage}</dt>
                  <dd>{stageLabel(stage)}</dd>
                </div>
                <div>
                  <dt>{labels.probability}</dt>
                  <dd>%{probability}</dd>
                </div>
                <div>
                  <dt>{labels.assigned}</dt>
                  <dd>{investor.assigned_to ?? '—'}</dd>
                </div>
                <div>
                  <dt>{labels.expectedClose}</dt>
                  <dd>{formatShortDate(investor.next_follow_up_date, locale)}</dd>
                </div>
                <div>
                  <dt>{labels.priority}</dt>
                  <dd>{priorityLabel(priority)}</dd>
                </div>
                <div>
                  <dt>{labels.nextAction}</dt>
                  <dd>{nextAction || '—'}</dd>
                </div>
              </dl>
              <div className="inv-g3-drawer__section">
                <h3>{labels.quickFields}</h3>
                <label className="inv-g3-drawer__field">
                  {labels.assigned}
                  <input value={assigned} onChange={(e) => setAssigned(e.target.value)} disabled={!canUpdate} />
                </label>
                <label className="inv-g3-drawer__field">
                  {labels.expectedClose}
                  <input
                    type="date"
                    value={closeDate}
                    onChange={(e) => setCloseDate(e.target.value)}
                    disabled={!canUpdate}
                  />
                </label>
                <label className="inv-g3-drawer__field">
                  {labels.capacity}
                  <input
                    type="number"
                    value={capacity}
                    onChange={(e) => setCapacity(e.target.value)}
                    disabled={!canUpdate}
                  />
                </label>
                <label className="inv-g3-drawer__field">
                  {labels.probability}
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={probability}
                    onChange={(e) => setProbability(e.target.value)}
                    disabled={!canUpdate}
                  />
                </label>
                <p className="inv-g3__banner inv-g3__banner--gap">{labels.probabilityGap}</p>
              </div>
            </>
          ) : null}

          {tab === 'profile' ? (
            <dl className="inv-g3-drawer__grid">
              <div>
                <dt>{labels.type}</dt>
                <dd>{typeLabel(investor.investor_type)}</dd>
              </div>
              <div>
                <dt>{labels.accreditation}</dt>
                <dd>{accreditationLabel(investor.accreditation_status)}</dd>
              </div>
              <div>
                <dt>{labels.model}</dt>
                <dd>{modelLabel(investor.preferred_investment_model)}</dd>
              </div>
              <div>
                <dt>{labels.risk}</dt>
                <dd>{riskLabel(investor.risk_profile)}</dd>
              </div>
              <div>
                <dt>{labels.markets}</dt>
                <dd>{investor.preferred_markets ?? '—'}</dd>
              </div>
              <div>
                <dt>{labels.projects}</dt>
                <dd>{investor.preferred_projects ?? '—'}</dd>
              </div>
              <div>
                <dt>{labels.source}</dt>
                <dd>{investor.source ?? '—'}</dd>
              </div>
              <div>
                <dt>{labels.statusLegacy}</dt>
                <dd>{statusLabel(investor.status)}</dd>
              </div>
              <div>
                <dt>{labels.minTicket}</dt>
                <dd>{formatCurrency(investor.minimum_ticket, locale)}</dd>
              </div>
              <div>
                <dt>{labels.maxTicket}</dt>
                <dd>{formatCurrency(investor.maximum_ticket, locale)}</dd>
              </div>
              <div>
                <dt>{labels.created}</dt>
                <dd>{formatDate(investor.created_at, locale)}</dd>
              </div>
              <div>
                <dt>{labels.updated}</dt>
                <dd>{formatDate(investor.updated_at, locale)}</dd>
              </div>
              <div>
                <dt>{labels.unsupported}</dt>
                <dd>{labels.unsupportedFields}</dd>
              </div>
            </dl>
          ) : null}

          {tab === 'stage' ? (
            <div className="inv-g3-drawer__section">
              <label className="inv-g3-drawer__field">
                {labels.stage}
                <select
                  value={nextStage}
                  onChange={(e) => setNextStage(e.target.value as InvestorLifecycleStage)}
                  disabled={!canUpdate}
                >
                  {INVESTOR_LIFECYCLE_STAGES.map((s) => (
                    <option key={s} value={s}>
                      {stageLabel(s)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="inv-g3-drawer__field">
                {labels.stageNote}
                <textarea
                  rows={3}
                  value={stageNote}
                  onChange={(e) => setStageNote(e.target.value)}
                  disabled={!canUpdate}
                />
              </label>
              <label className="inv-g3-drawer__field">
                {labels.priority}
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as InvestorPriority)}
                  disabled={!canUpdate}
                >
                  {(['low', 'medium', 'high', 'urgent'] as InvestorPriority[]).map((p) => (
                    <option key={p} value={p}>
                      {priorityLabel(p)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="inv-g3-drawer__field">
                {labels.nextAction}
                <input value={nextAction} onChange={(e) => setNextAction(e.target.value)} disabled={!canUpdate} />
              </label>
              <button
                type="button"
                className="inv-g3__btn inv-g3__btn--primary"
                disabled={!canUpdate || saving || nextStage === stage}
                onClick={async () => {
                  saveMetaLocal();
                  appendStageHistory(investor.id, {
                    from: stage,
                    to: nextStage,
                    at: new Date().toISOString(),
                    note: stageNote || undefined,
                  });
                  onMetaChange();
                  await onStageChange(investor, nextStage, stageNote || undefined);
                }}
              >
                {labels.applyStage}
              </button>
              <div className="inv-g3-drawer__section">
                <h3>{labels.stageHistory}</h3>
                {(meta.stageHistory?.length ?? 0) === 0 ? (
                  <p className="inv-g3__empty">{labels.noHistory}</p>
                ) : (
                  <ul className="inv-g3-drawer__history">
                    {[...(meta.stageHistory ?? [])].reverse().map((h, idx) => (
                      <li key={`${h.at}-${idx}`}>
                        <strong>
                          {stageLabel(toLifecycleStage(h.from))} → {stageLabel(toLifecycleStage(h.to))}
                        </strong>
                        <div>{formatDate(h.at, locale)}</div>
                        {h.note ? <div>{h.note}</div> : null}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ) : null}

          {tab === 'notes' ? (
            <label className="inv-g3-drawer__field">
              {labels.notes}
              <textarea
                rows={10}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={!canUpdate}
              />
            </label>
          ) : null}

          {tab === 'activity' ? (
            <EntityActivityTimeline entityType="investor" entityId={investor.id} />
          ) : null}

          {tab === 'documents' ? (
            <EntityDocumentsPanel entityType="investor" entityId={investor.id} />
          ) : null}

          {tab === 'ai' ? (
            <div className="inv-g3-drawer__section">
              <p className="inv-g3__banner inv-g3__banner--info">{labels.aiHint}</p>
              <ContextualAiActions module="investor" />
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
