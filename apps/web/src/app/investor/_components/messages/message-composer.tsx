'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { sanitizePlainText } from '../../_utils/sanitize-text';
import { useMessagingState } from '../../_state/messaging-state';

interface MessageComposerProps {
  conversationId: string;
  onSent?: () => void;
}

export function MessageComposer({ conversationId, onSent }: MessageComposerProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const t = useTranslations('investorPortal');
  const { getDraft, saveDraft, clearDraft, sendMessage } = useMessagingState();
  const [body, setBody] = useState('');
  const [attachMock, setAttachMock] = useState(false);

  useEffect(() => {
    setBody(getDraft(conversationId));
  }, [conversationId, getDraft]);

  const handleChange = useCallback(
    (value: string) => {
      setBody(value);
      saveDraft(conversationId, value);
    },
    [conversationId, saveDraft],
  );

  const handleSend = useCallback(() => {
    const trimmed = sanitizePlainText(body, 5000);
    if (!trimmed) return;
    sendMessage(conversationId, trimmed);
    setBody('');
    clearDraft(conversationId);
    onSent?.();
  }, [body, conversationId, sendMessage, clearDraft, onSent]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="inv-msg-composer" role="form" aria-label={tChrome('ke6172c488b')}>
      <textarea
        className="inv-msg-composer__input"
        value={body}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t('placeholders.message')}
        rows={3}
        aria-label={tChrome('k723e79cd24')}
      />
      <div className="inv-msg-composer__toolbar">
        <button
          type="button"
          className={`inv-msg-composer__tool${attachMock ? ' inv-msg-composer__tool--active' : ''}`}
          onClick={() => setAttachMock((v) => !v)}
          aria-pressed={attachMock}
          title={tChrome('kc266c5717c')}
        >
          📎 Attach
        </button>
        <button type="button" className="inv-msg-composer__tool" title={tChrome('k5b02e26fcf')} disabled>
          🔗 Reference
        </button>
        {attachMock ? (
          <span className="inv-msg-composer__mock-att">{tChrome('k163d828a3b')}</span>
        ) : null}
        <div className="inv-msg-composer__actions">
          <button
            type="button"
            className="inv-msg-composer__draft"
            onClick={() => saveDraft(conversationId, body)}
          >
            Save draft
          </button>
          <button
            type="button"
            className="inv-msg-composer__send"
            onClick={handleSend}
            disabled={!body.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
