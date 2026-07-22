'use client';

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
  const { completeTask } = useMessagingState();
  const isComplete = task.status === 'completed';

  return (
    <div className="inv-task-detail">
      <nav className="inv-task-detail__back" aria-label="Breadcrumb">
        <Link href={'/investor/tasks' as Route}>← Back to Tasks</Link>
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
          <span className="inv-task-detail__meta-label">Due date</span>
          <time dateTime={task.dueDate}>{formatInvestorDate(task.dueDate)}</time>
        </div>
        <div>
          <span className="inv-task-detail__meta-label">Owner</span>
          <span>{task.owner.name} ({task.owner.role})</span>
        </div>
        <div>
          <span className="inv-task-detail__meta-label">Assignee</span>
          <span>{task.assignee.name}</span>
        </div>
        <div>
          <span className="inv-task-detail__meta-label">Last updated</span>
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
        <h2>Description</h2>
        <p>{task.description}</p>
      </section>

      <div className="inv-task-detail__grid">
        <div className="inv-task-detail__main">
          <TaskChecklist taskId={task.id} checklist={task.checklist} />

          <TaskReminders reminders={task.reminders} />

          {task.attachments.length > 0 ? (
            <section className="inv-task-detail__attachments" aria-labelledby="attachments-title">
              <h3 id="attachments-title">Attachments</h3>
              <ul>
                {task.attachments.map((att) => (
                  <li key={att.id}>
                    <button type="button" disabled title="Demo only">
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
              <h3 id="related-title">Related Items</h3>
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
                    <Link href={`/investor/messages/${id}` as Route}>Message thread</Link>
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
