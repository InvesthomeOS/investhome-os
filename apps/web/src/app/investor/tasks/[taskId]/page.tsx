'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams } from 'next/navigation';
import { useMemo } from 'react';

import { EmptyState } from '../../_components/empty-state';
import { TaskDetailView } from '../../_components/tasks/task-detail-view';
import { useMessagingState } from '../../_state/messaging-state';
import type { Task } from '../../_data/messaging-types';

export default function TaskDetailPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params.taskId;
  const { tasks } = useMessagingState();

  const task = useMemo(() => tasks.find((t: Task) => t.id === taskId), [tasks, taskId]);

  if (!task) {
    return (
      <div className="investor-page">
        <EmptyState
          icon="☑"
          title="Task not found"
          description="This task may have been completed or removed."
          actionLabel="Back to tasks"
          onAction={() => {}}
        />
        <Link href={'/investor/tasks' as Route} className="inv-task-detail__back">
          ← Back to Tasks
        </Link>
      </div>
    );
  }

  return (
    <div className="investor-page">
      <TaskDetailView task={task} />
    </div>
  );
}
