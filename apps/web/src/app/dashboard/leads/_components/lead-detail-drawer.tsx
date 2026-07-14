'use client';

import { formatBudget, formatDate, type Lead } from '@/lib/api/leads';

interface LeadDetailDrawerProps {
  lead: Lead | null;
  archiving: boolean;
  onClose: () => void;
  onEdit: (lead: Lead) => void;
  onArchive: (lead: Lead) => void;
}

export function LeadDetailDrawer({
  lead,
  archiving,
  onClose,
  onEdit,
  onArchive,
}: LeadDetailDrawerProps) {
  if (!lead) {
    return null;
  }

  return (
    <div className="leads-drawer" role="presentation" onClick={onClose}>
      <aside
        className="leads-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lead-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="leads-drawer__header">
          <div>
            <p className="dashboard__eyebrow">Lead detail</p>
            <h2 id="lead-detail-title">{lead.full_name}</h2>
            {lead.is_demo && <span className="leads__demo-tag">Demo data</span>}
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>
            Close
          </button>
        </header>

        <dl className="leads-drawer__grid">
          <div>
            <dt>Email</dt>
            <dd>{lead.email ?? '—'}</dd>
          </div>
          <div>
            <dt>Phone</dt>
            <dd>{lead.phone ?? '—'}</dd>
          </div>
          <div>
            <dt>Country</dt>
            <dd>{lead.country ?? '—'}</dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{lead.source ?? '—'}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{lead.status}</dd>
          </div>
          <div>
            <dt>Assigned to</dt>
            <dd>{lead.assigned_to ?? '—'}</dd>
          </div>
          <div>
            <dt>Budget</dt>
            <dd>{formatBudget(lead.estimated_budget)}</dd>
          </div>
          <div>
            <dt>Project</dt>
            <dd>{lead.interested_project ?? '—'}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDate(lead.created_at)}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDate(lead.updated_at)}</dd>
          </div>
        </dl>

        <div className="leads-drawer__notes">
          <h3>Notes</h3>
          <p>{lead.notes?.trim() ? lead.notes : 'No notes recorded.'}</p>
        </div>

        <footer className="leads-drawer__footer">
          <button type="button" className="leads__button leads__button--secondary" onClick={() => onEdit(lead)}>
            Edit
          </button>
          <button
            type="button"
            className="leads__button leads__button--danger"
            disabled={archiving}
            onClick={() => onArchive(lead)}
          >
            {archiving ? 'Archiving…' : 'Archive Lead'}
          </button>
        </footer>
      </aside>
    </div>
  );
}
