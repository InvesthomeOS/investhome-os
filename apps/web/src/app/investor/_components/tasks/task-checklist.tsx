'use client';

import { useTranslations } from 'next-intl';

import type { TaskChecklist as TaskChecklistType } from '../../_data/messaging-types';
import { useMessagingState } from '../../_state/messaging-state';

interface TaskChecklistProps {
  taskId: string;
  checklist: TaskChecklistType;
}

export function TaskChecklist({ taskId, checklist }: TaskChecklistProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const { toggleChecklistItem } = useMessagingState();
  const completed = checklist.items.filter((i) => i.isCompleted).length;
  const total = checklist.items.length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <section className="inv-task-checklist" aria-labelledby="checklist-title">
      <div className="inv-task-checklist__header">
        <h3 id="checklist-title">{checklist.title}</h3>
        <span className="inv-task-checklist__progress" aria-live="polite">
          {percent}% complete ({completed}/{total})
        </span>
      </div>

      <div
        className="inv-task-checklist__bar"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={tChrome('kd3f60983f9')}
      >
        <div className="inv-task-checklist__bar-fill" style={{ width: `${percent}%` }} />
      </div>

      <ul className="inv-task-checklist__list">
        {checklist.items.map((item) => (
          <li key={item.id}>
            <label className="inv-task-checklist__item">
              <input
                type="checkbox"
                checked={item.isCompleted}
                onChange={() => toggleChecklistItem(taskId, item.id)}
                aria-label={item.label}
              />
              <span className={item.isCompleted ? 'inv-task-checklist__done' : ''}>
                {item.label}
              </span>
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}
