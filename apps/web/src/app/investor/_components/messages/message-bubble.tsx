'use client';

import { sanitizePlainText } from '../../_utils/sanitize-text';
import type { Message, MessageReference } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';

interface MessageBubbleProps {
  message: Message;
  showAuthor?: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MessageBubble({ message, showAuthor = true }: MessageBubbleProps) {
  const isInvestor = message.author.isInvestor;
  const body = sanitizePlainText(message.body, 5000);

  return (
    <article
      className={`inv-msg-bubble${isInvestor ? ' inv-msg-bubble--outgoing' : ' inv-msg-bubble--incoming'}${message.isPinned ? ' inv-msg-bubble--pinned' : ''}`}
      aria-label={`Message from ${message.author.name}`}
    >
      {showAuthor && !isInvestor ? (
        <header className="inv-msg-bubble__header">
          <span className="inv-msg-bubble__avatar" aria-hidden="true">
            {message.author.avatarInitials}
          </span>
          <div>
            <strong className="inv-msg-bubble__author">{message.author.name}</strong>
            <span className="inv-msg-bubble__role">{message.author.role}</span>
          </div>
        </header>
      ) : null}

      <div className="inv-msg-bubble__body">
        <p>{body}</p>
        {message.attachments.length > 0 ? (
          <ul className="inv-msg-bubble__attachments" aria-label="Attachments">
            {message.attachments.map((att) => (
              <li key={att.id}>
                <button type="button" className="inv-msg-bubble__attachment" disabled title="Demo only">
                  <span aria-hidden="true">📎</span>
                  <span>{att.fileName}</span>
                  <span className="inv-msg-bubble__file-size">{formatFileSize(att.fileSizeBytes)}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {message.references.length > 0 ? (
          <ul className="inv-msg-bubble__refs" aria-label="Related items">
            {message.references.map((ref: MessageReference) => (
              <li key={`${ref.type}-${ref.id}`}>
                <span className="inv-msg-bubble__ref-badge">{ref.type}</span>
                {ref.label}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <footer className="inv-msg-bubble__footer">
        <time dateTime={message.sentAt}>{formatInvestorDateTime(message.sentAt)}</time>
        {message.isPinned ? <span className="inv-msg-bubble__pin" aria-label="Pinned">📌</span> : null}
        {!message.isRead && !isInvestor ? (
          <span className="inv-msg-bubble__unread" aria-label="Unread">Unread</span>
        ) : null}
      </footer>
    </article>
  );
}
