'use client';

import {
  ISSUE_COLUMNS,
  PROJECTS,
  formatShortDate,
  type ConstructionIssue,
} from './demo-data';

const PRIO_TR: Record<ConstructionIssue['priority'], string> = {
  urgent: 'Acil',
  high: 'Yüksek',
  medium: 'Orta',
  low: 'Düşük',
};

type Props = {
  issue: ConstructionIssue;
  onClose: () => void;
};

export function IssueDrawer({ issue, onClose }: Props) {
  const status = ISSUE_COLUMNS.find((c) => c.id === issue.status);
  const project = PROJECTS.find((p) => p.id === issue.projectId);

  return (
    <div className="g1-drawer-root" role="dialog" aria-modal="true" data-testid="g1-issue-drawer">
      <button type="button" className="g1-drawer-scrim" aria-label="Kapat" onClick={onClose} />
      <aside className="g1-drawer">
        <header className="g1-drawer__head">
          <div>
            <p className="g1-drawer__kicker">{issue.key}</p>
            <h2 className="g1-drawer__title">{issue.title}</h2>
          </div>
          <button type="button" className="g1-drawer__close" onClick={onClose} aria-label="Kapat">
            ×
          </button>
        </header>
        <div className="g1-drawer__body">
          <div className="g1-drawer__person">
            <span className="g1-avatar" aria-hidden>
              {issue.initials}
            </span>
            <div>
              <strong>{issue.assignee}</strong>
              <span>{project?.name ?? 'Proje'}</span>
            </div>
          </div>

          <div className="g1-field-grid">
            <div className="g1-field">
              <label>Durum</label>
              <p>{status?.labelTr ?? issue.status}</p>
            </div>
            <div className="g1-field">
              <label>Öncelik</label>
              <p>
                <span className={`g1-prio g1-prio--${issue.priority}`}>{PRIO_TR[issue.priority]}</span>
              </p>
            </div>
            <div className="g1-field">
              <label>Son tarih</label>
              <p>{formatShortDate(issue.due)}</p>
            </div>
            <div className="g1-field">
              <label>Blokör</label>
              <p>{issue.blockers > 0 ? `${issue.blockers} blokör` : 'Yok'}</p>
            </div>
            <div className="g1-field g1-field--full">
              <label>Etiketler</label>
              <p>
                <span className="g1-labels">
                  {issue.labels.map((l) => (
                    <span key={l} className="g1-label">
                      {l}
                    </span>
                  ))}
                </span>
              </p>
            </div>
            <div className="g1-field g1-field--full">
              <label>Açıklama</label>
              <p className="g1-drawer__notes">{issue.description}</p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
