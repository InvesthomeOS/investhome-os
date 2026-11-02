'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Suspense } from 'react';

import { CrmCalendarWorkspace } from '../calendar/_components/crm-calendar-workspace';
import { CrmTasksWorkspace } from './_components/crm-tasks-workspace';
import '@/workspaces/crm/contact-card/contact-card.css';
import '../calendar/calendar-ops.css';
import './tasks-ops.css';

function TasksPageBody() {
  const params = useSearchParams();
  const t = useTranslations('crm.tasks');
  const calendar = params.get('view') === 'calendar';

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-tasks-page">
      <nav className="crm-ops-views crm-task-views" aria-label={t('viewAria')}>
        <Link href={'/workspaces/crm/tasks' as Route} className={calendar ? undefined : 'is-active'}>
          {t('views.list')}
        </Link>
        <Link
          href={'/workspaces/crm/tasks?view=calendar' as Route}
          className={calendar ? 'is-active' : undefined}
        >
          {t('views.calendar')}
        </Link>
      </nav>
      {calendar ? <CrmCalendarWorkspace /> : <CrmTasksWorkspace />}
    </main>
  );
}

export default function CrmTasksPage() {
  return (
    <Suspense fallback={null}>
      <TasksPageBody />
    </Suspense>
  );
}
