'use client';

import { useState } from 'react';

import { sanitizePlainText } from '../../_utils/sanitize-text';
import type { TaskComment } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';
import { useMessagingState } from '../../_state/messaging-state';

interface TaskCommentsProps {
  taskId: string;
  comments: TaskComment[];
}

export function TaskComments({ taskId, comments }: TaskCommentsProps) {
  const { addTaskComment } = useMessagingState();
  const [body, setBody] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = sanitizePlainText(body, 2000);
    if (!trimmed) return;
    addTaskComment(taskId, trimmed);
    setBody('');
  };

  return (
    <section className="inv-task-comments" aria-labelledby="comments-title">
      <h3 id="comments-title">Comments</h3>

      {comments.length === 0 ? (
        <p className="inv-task-comments__empty">No comments yet.</p>
      ) : (
        <ul className="inv-task-comments__list">
          {comments.map((comment) => (
            <li key={comment.id} className="inv-task-comments__item">
              <div className="inv-task-comments__author">
                <span className="inv-task-comments__avatar" aria-hidden="true">
                  {comment.author.avatarInitials}
                </span>
                <div>
                  <strong>{comment.author.name}</strong>
                  <span>{comment.author.role}</span>
                </div>
              </div>
              <p>{sanitizePlainText(comment.body, 2000)}</p>
              <time dateTime={comment.createdAt}>
                {formatInvestorDateTime(comment.createdAt)}
              </time>
            </li>
          ))}
        </ul>
      )}

      <form className="inv-task-comments__form" onSubmit={handleSubmit}>
        <label htmlFor="task-comment-input" className="visually-hidden">
          Add comment
        </label>
        <textarea
          id="task-comment-input"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment…"
          rows={3}
        />
        <button type="submit" disabled={!body.trim()}>
          Post comment
        </button>
      </form>
    </section>
  );
}
