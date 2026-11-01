'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { Task } from '../../_data/messaging-types';
import { formatInvestorDate, formatInvestorDateTime } from '../../_data/mock-data';
import { useMessagingState } from '../../_state/messaging-state';
import { MockUpload } from './mock-upload';
import { TaskActivityTimeline } from './task-activity-timeline';
import { TaskChecklist } from './task-checklist';
import { TaskComments } from './task-comments';
import { TaskReminders } from './task-reminders';

interface TaskDetailViewProps {
  task: Task;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function TaskDetailView({ task }: TaskDetailViewProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const { completeTask } = useMessagingState();
  const isComplete = task.status === 'completed';

  return (
    <div className="inv-task-detail">
      <nav className="inv-task-detail__back" aria-label={tChrome('kc766e66518')}>
        <Link href={'/investor/tasks' as Route}>{tChrome('kf87efea85f')}</Link>
      </nav>

      <header className="inv-task-detail__header">
        <div>
          <h1 className="inv-task-detail__title">{task.title}</h1>
          <p className="inv-task-detail__investment">{task.investmentName}</p>
        </div>
        <div className="inv-task-detail__badges">
          <span className={`inv-task-detail__status inv-task-detail__status--${task.status}`}>
            {task.status.replace(/_/g, ' ')}
          </span>
          <span className={`inv-task-detail__priority inv-task-detail__priority--${task.priority}`}>
            {task.priority}
          </span>
          <span className="inv-task-detail__category">{task.category.replace(/_/g, ' ')}</span>
        </div>
      </header>

      <div className="inv-task-detail__meta-grid">
        <div>
          <span className="inv-task-detail__meta-label">{tChrome('k4c1aeebc43')}</span>
          <time dateTime={task.dueDate}>{formatInvestorDate(task.dueDate)}</time>
        </div>
        <div>
          <span className="inv-task-detail__meta-label">{tChrome('k89ff31225c')}</span>
          <span>{task.owner.name} ({task.owner.role})</span>
        </div>
        <div>
          <span className="inv-task-detail__meta-label">{tChrome('k049e3ce547')}</span>
          <span>{task.assignee.name}</span>
        </div>
        <div>
          <span className="inv-task-detail__meta-label">{tChrome('k583c9e2357')}</span>
          <time dateTime={task.updatedAt}>{formatInvestorDateTime(task.updatedAt)}</time>
        </div>
      </div>

      {!isComplete ? (
        <div className="inv-task-detail__actions">
          <button type="button" className="inv-task-detail__complete" onClick={() => completeTask(task.id)}>
            Mark complete
          </button>
        </div>
      ) : null}

      <section className="inv-task-detail__description">
        <h2>{tChrome('k55f8ebc805')}</h2>
        <p>{task.description}</p>
      </section>

      <div className="inv-task-detail__grid">
        <div className="inv-task-detail__main">
          <TaskChecklist taskId={task.id} checklist={task.checklist} />

          <TaskReminders reminders={task.reminders} />

          {task.attachments.length > 0 ? (
            <section className="inv-task-detail__attachments" aria-labelledby="attachments-title">
              <h3 id="attachments-title">{tChrome('k6771ade6e8')}</h3>
              <ul>
                {task.attachments.map((att) => (
                  <li key={att.id}>
                    <button type="button" disabled title={tChrome('kbb23f6a3e1')}>
                      📎 {att.fileName} ({formatFileSize(att.fileSizeBytes)})
                    </button>
                    <span>Uploaded by {att.uploadedBy}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <MockUpload label="Upload supporting documents" />

          <TaskComments taskId={task.id} comments={task.comments} />
        </div>

        <aside className="inv-task-detail__sidebar">
          {(task.relatedDocumentIds.length > 0 ||
            task.relatedSignatureIds.length > 0 ||
            task.relatedConversationIds.length > 0 ||
            task.relatedDistributionIds.length > 0) && (
            <section className="inv-task-detail__related" aria-labelledby="related-title">
              <h3 id="related-title">{tChrome('k5b2acaa785')}</h3>
              <ul>
                {task.relatedDocumentIds.map((id) => (
                  <li key={id}>
                    <Link href={'/investor/documents' as Route}>Document: {id}</Link>
                  </li>
                ))}
                {task.relatedSignatureIds.map((id) => (
                  <li key={id}>
                    <Link href={'/investor/documents' as Route}>Signature: {id}</Link>
                  </li>
                ))}
                {task.relatedConversationIds.map((id) => (
                  <li key={id}>
                    <Link href={`/investor/messages/${id}` as Route}>{tChrome('k59be495db7')}</Link>
                  </li>
                ))}
                {task.relatedDistributionIds.map((id) => (
                  <li key={id}>
                    <Link href={'/investor/distributions' as Route}>Distribution: {id}</Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <TaskActivityTimeline activity={task.activity} />
        </aside>
      </div>
    </div>
  );
}
