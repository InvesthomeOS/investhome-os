'use client';

import {
  STAGE_META,
  formatShortDate,
  formatTry,
  type Opportunity,
} from './demo-data';

type Props = {
  opportunity: Opportunity;
  onClose: () => void;
};

export function OpportunityDrawer({ opportunity, onClose }: Props) {
  const stage = STAGE_META.find((s) => s.id === opportunity.stage);

  return (
    <div className="g1-drawer-root" role="dialog" aria-modal="true" data-testid="g1-opp-drawer">
      <button type="button" className="g1-drawer-scrim" aria-label="Kapat" onClick={onClose} />
      <aside className="g1-drawer">
        <header className="g1-drawer__head">
          <div>
            <p className="g1-drawer__kicker">Fırsat detayı</p>
            <h2 className="g1-drawer__title">{opportunity.title}</h2>
          </div>
          <button type="button" className="g1-drawer__close" onClick={onClose} aria-label="Kapat">
            ×
          </button>
        </header>
        <div className="g1-drawer__body">
          <div className="g1-drawer__person">
            <span className="g1-avatar" aria-hidden>
              {opportunity.initials}
            </span>
            <div>
              <strong>{opportunity.investor}</strong>
              <span>
                {opportunity.company} · {opportunity.type === 'investor' ? 'Yatırımcı' : 'Satış'}
              </span>
            </div>
          </div>

          <div className="g1-field-grid">
            <div className="g1-field">
              <label>Aşama</label>
              <p>{stage?.labelTr ?? opportunity.stage}</p>
            </div>
            <div className="g1-field">
              <label>Değer</label>
              <p>{formatTry(opportunity.valueTry)}</p>
            </div>
            <div className="g1-field">
              <label>Olasılık</label>
              <p>%{opportunity.probability}</p>
            </div>
            <div className="g1-field">
              <label>Beklenen kapanış</label>
              <p>{formatShortDate(opportunity.closeDate)}</p>
            </div>
            <div className="g1-field">
              <label>Proje</label>
              <p>{opportunity.project}</p>
            </div>
            <div className="g1-field">
              <label>Sahip</label>
              <p>{opportunity.owner}</p>
            </div>
            <div className="g1-field">
              <label>E-posta</label>
              <p>{opportunity.email}</p>
            </div>
            <div className="g1-field">
              <label>Telefon</label>
              <p>{opportunity.phone}</p>
            </div>
            <div className="g1-field g1-field--full">
              <label>Notlar</label>
              <p className="g1-drawer__notes">{opportunity.notes}</p>
            </div>
          </div>

          <div className="g1-field g1-field--full">
            <label>Son aktivite</label>
            <ul className="g1-activity">
              <li>
                <span>Bugün</span>
                <p>Sahip atandı · {opportunity.owner}</p>
              </li>
              <li>
                <span>Dün</span>
                <p>Aşama: {stage?.labelTr ?? opportunity.stage}</p>
              </li>
              <li>
                <span>3g</span>
                <p>Not eklendi · keşif özeti</p>
              </li>
            </ul>
          </div>
        </div>
      </aside>
    </div>
  );
}
