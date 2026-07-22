'use client';

import { useState } from 'react';

import { sanitizePlainText } from '../../_utils/sanitize-text';
import { getAllInvestments } from '../../_data/investments';
import { IR_TEAM_MEMBERS } from '../../_data/conversations';

interface ComposeModalProps {
  open: boolean;
  onClose: () => void;
}

export function ComposeModal({ open, onClose }: ComposeModalProps) {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [investmentId, setInvestmentId] = useState('');
  const [sent, setSent] = useState(false);

  const investments = getAllInvestments();

  if (!open) return null;

  const handleSend = () => {
    const trimmed = sanitizePlainText(body, 5000);
    if (!trimmed || !subject.trim()) return;
    setSent(true);
    setTimeout(() => {
      setSent(false);
      setSubject('');
      setBody('');
      setInvestmentId('');
      onClose();
    }, 1500);
  };

  return (
    <>
      <button type="button" className="inv-panel-overlay" onClick={onClose} aria-label="Close" />
      <div
        className="inv-compose-modal"
        role="dialog"
        aria-labelledby="compose-title"
        aria-modal="true"
      >
        <header className="inv-compose-modal__header">
          <h2 id="compose-title">Compose Message</h2>
          <button type="button" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        {sent ? (
          <div className="inv-compose-modal__success" role="status">
            Message queued for delivery (demo).
          </div>
        ) : (
          <div className="inv-compose-modal__body">
            <label className="inv-compose-modal__field">
              To
              <select defaultValue={IR_TEAM_MEMBERS.sarah.id} aria-label="Recipient">
                <option value={IR_TEAM_MEMBERS.sarah.id}>
                  {IR_TEAM_MEMBERS.sarah.name} — {IR_TEAM_MEMBERS.sarah.role}
                </option>
                <option value={IR_TEAM_MEMBERS.marcus.id}>
                  {IR_TEAM_MEMBERS.marcus.name} — {IR_TEAM_MEMBERS.marcus.role}
                </option>
                <option value={IR_TEAM_MEMBERS.elena.id}>
                  {IR_TEAM_MEMBERS.elena.name} — {IR_TEAM_MEMBERS.elena.role}
                </option>
              </select>
            </label>

            <label className="inv-compose-modal__field">
              Investment (optional)
              <select
                value={investmentId}
                onChange={(e) => setInvestmentId(e.target.value)}
                aria-label="Related investment"
              >
                <option value="">General inquiry</option>
                {investments.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.projectName}
                  </option>
                ))}
              </select>
            </label>

            <label className="inv-compose-modal__field">
              Subject
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Message subject"
              />
            </label>

            <label className="inv-compose-modal__field">
              Message
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={6}
                placeholder="Write your message…"
              />
            </label>

            <div className="inv-compose-modal__tools">
              <button type="button" disabled title="Demo only">
                📎 Attach
              </button>
              <button type="button" disabled title="Demo only">
                🔗 Add reference
              </button>
            </div>
          </div>
        )}

        {!sent ? (
          <footer className="inv-compose-modal__footer">
            <button type="button" className="inv-compose-modal__cancel" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="inv-compose-modal__send"
              onClick={handleSend}
              disabled={!subject.trim() || !body.trim()}
            >
              Send message
            </button>
          </footer>
        ) : null}
      </div>
    </>
  );
}
