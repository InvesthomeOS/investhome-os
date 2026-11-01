'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { Task } from '../../_data/messaging-types';
import { formatInvestorDate } from '../../_data/mock-data';

interface TaskTableProps {
  tasks: Task[];
}

const STATUS_CLASS: Record<Task['status'], string> = {
  open: 'inv-task-table__status--open',
  in_progress: 'inv-task-table__status--progress',
  pending_review: 'inv-task-table__status--review',
  completed: 'inv-task-table__status--completed',
  overdue: 'inv-task-table__status--overdue',
  cancelled: 'inv-task-table__status--cancelled',
};

const PRIORITY_CLASS: Record<Task['priority'], string> = {
  critical: 'inv-task-table__priority--critical',
  high: 'inv-task-table__priority--high',
  medium: 'inv-task-table__priority--medium',
  low: 'inv-task-table__priority--low',
};

export function TaskTable({ tasks }: TaskTableProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  if (tasks.length === 0) {
    return (
      <div className="inv-task-table__empty">
        <p>{tChrome('k462bb6a249')}</p>
      </div>
    );
  }

  return (
    <div className="inv-task-table__wrap">
      <table className="inv-task-table" aria-label={tChrome('k090ec5f560')}>
        <thead>
          <tr>
            <th scope="col">{tChrome('k7bb0ddf922')}</th>
            <th scope="col">{tChrome('k0401729c31')}</th>
            <th scope="col">{tChrome('ka3c686e711')}</th>
            <th scope="col">{tChrome('k886cbff9d9')}</th>
            <th scope="col">{tChrome('kbae7d5be70')}</th>
            <th scope="col">{tChrome('ka1b308ec70')}</th>
            <th scope="col">{tChrome('k1b90271d66')}</th>
            <th scope="col">{tChrome('k049e3ce547')}</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id}>
              <td>
                <Link href={`/investor/tasks/${task.id}` as Route} className="inv-task-table__link">
                  {task.title}
                </Link>
              </td>
              <td>{task.investmentName}</td>
              <td>
                <span className="inv-task-table__category">
                  {task.category.replace(/_/g, ' ')}
                </span>
              </td>
              <td>
                <span className={`inv-task-table__priority ${PRIORITY_CLASS[task.priority]}`}>
                  {task.priority}
                </span>
              </td>
              <td>
                <span className={`inv-task-table__status ${STATUS_CLASS[task.status]}`}>
                  {task.status.replace(/_/g, ' ')}
                </span>
              </td>
              <td>
                <time dateTime={task.dueDate}>{formatInvestorDate(task.dueDate)}</time>
              </td>
              <td>
                <div className="inv-task-table__progress" role="progressbar" aria-valuenow={task.progressPercent} aria-valuemin={0} aria-valuemax={100}>
                  <div
                    className="inv-task-table__progress-bar"
                    style={{ width: `${task.progressPercent}%` }}
                  />
                  <span>{task.progressPercent}%</span>
                </div>
              </td>
              <td>
                <span className="inv-task-table__assignee" title={task.assignee.emailMasked}>
                  {task.assignee.avatarInitials}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <ul className="inv-task-table__mobile" aria-label={tChrome('k090ec5f560')}>
        {tasks.map((task) => (
          <li key={task.id} className="inv-task-table__mobile-card">
            <Link href={`/investor/tasks/${task.id}` as Route}>
              <strong>{task.title}</strong>
              <span>{task.investmentName}</span>
              <div className="inv-task-table__mobile-meta">
                <span className={`inv-task-table__status ${STATUS_CLASS[task.status]}`}>
                  {task.status.replace(/_/g, ' ')}
                </span>
                <time dateTime={task.dueDate}>Due {formatInvestorDate(task.dueDate)}</time>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
