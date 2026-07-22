'use client';

import { useCallback, useEffect, useState } from 'react';

import { sanitizePlainText } from '../../_utils/sanitize-text';
import { useMessagingState } from '../../_state/messaging-state';

interface MessageComposerProps {
  conversationId: string;
  onSent?: () => void;
}

export function MessageComposer({ conversationId, onSent }: MessageComposerProps) {
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
    <div className="inv-msg-composer" role="form" aria-label="Compose message">
      <textarea
        className="inv-msg-composer__input"
        value={body}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your message… (Ctrl+Enter to send)"
        rows={3}
        aria-label="Message text"
      />
      <div className="inv-msg-composer__toolbar">
        <button
          type="button"
          className={`inv-msg-composer__tool${attachMock ? ' inv-msg-composer__tool--active' : ''}`}
          onClick={() => setAttachMock((v) => !v)}
          aria-pressed={attachMock}
          title="Attach file (demo)"
        >
          📎 Attach
        </button>
        <button type="button" className="inv-msg-composer__tool" title="Link reference (demo)" disabled>
          🔗 Reference
        </button>
        {attachMock ? (
          <span className="inv-msg-composer__mock-att">demo-document.pdf (mock)</span>
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
