'use client';

import { useTranslations } from 'next-intl';

import type { TaskReminder } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';

interface TaskRemindersProps {
  reminders: TaskReminder[];
}

export function TaskReminders({ reminders }: TaskRemindersProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const upcoming = reminders.filter((r) => r.status === 'upcoming');
  const dueToday = reminders.filter((r) => r.status === 'due_today');
  const overdue = reminders.filter((r) => r.status === 'overdue');
  const history = reminders.filter((r) => r.status === 'sent' || r.status === 'dismissed');

  if (reminders.length === 0) return null;

  return (
    <section className="inv-task-reminders" aria-labelledby="reminders-title">
      <h3 id="reminders-title">{tChrome('kae8c393938')}</h3>

      {dueToday.length > 0 ? (
        <div className="inv-task-reminders__group inv-task-reminders__group--today">
          <h4>{tChrome('ke2219e75f0')}</h4>
          <ul>
            {dueToday.map((r) => (
              <ReminderItem key={r.id} reminder={r} />
            ))}
          </ul>
        </div>
      ) : null}

      {overdue.length > 0 ? (
        <div className="inv-task-reminders__group inv-task-reminders__group--overdue">
          <h4>{tChrome('k07217c7719')}</h4>
          <ul>
            {overdue.map((r) => (
              <ReminderItem key={r.id} reminder={r} />
            ))}
          </ul>
        </div>
      ) : null}

      {upcoming.length > 0 ? (
        <div className="inv-task-reminders__group">
          <h4>{tChrome('k523baab918')}</h4>
          <ul>
            {upcoming.map((r) => (
              <ReminderItem key={r.id} reminder={r} />
            ))}
          </ul>
        </div>
      ) : null}

      {history.length > 0 ? (
        <div className="inv-task-reminders__group inv-task-reminders__group--history">
          <h4>{tChrome('k90ccd64974')}</h4>
          <ul>
            {history.map((r) => (
              <ReminderItem key={r.id} reminder={r} />
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function ReminderItem({ reminder }: { reminder: TaskReminder }) {
  return (
    <li className={`inv-task-reminders__item inv-task-reminders__item--${reminder.status}`}>
      <span>{reminder.label}</span>
      <time dateTime={reminder.scheduledAt}>
        {formatInvestorDateTime(reminder.scheduledAt)}
      </time>
    </li>
  );
}
