'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';
import type { ProjectMilestone } from '../../_data/investment-detail-types';

const STATUS_LABELS: Record<ProjectMilestone['status'], string> = {
  completed: 'Completed',
  in_progress: 'In Progress',
  upcoming: 'Upcoming',
  delayed: 'Delayed',
  at_risk: 'At Risk',
};

export interface MilestoneTimelineProps {
  milestones: ProjectMilestone[];
}

export function MilestoneTimeline({ milestones }: MilestoneTimelineProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <ol className="inv-milestone-timeline" aria-label={tChrome('k253767ebd5')}>
      {milestones.map((ms, index) => (
        <li
          key={ms.id}
          className={`inv-milestone-timeline__item inv-milestone-timeline__item--${ms.status}`}
        >
          <div className="inv-milestone-timeline__marker" aria-hidden="true">
            <span>{index + 1}</span>
          </div>
          <div className="inv-milestone-timeline__body">
            <div className="inv-milestone-timeline__header">
              <h4 className="inv-milestone-timeline__title">{ms.title}</h4>
              <span className={`inv-milestone-timeline__status inv-milestone-timeline__status--${ms.status}`}>
                {investorChrome(tChrome, STATUS_LABELS[ms.status])}
              </span>
            </div>
            <p className="inv-milestone-timeline__desc">{ms.description}</p>
            <div className="inv-milestone-timeline__meta">
              <span className="inv-milestone-timeline__phase">{ms.phase}</span>
              <time dateTime={ms.targetDate}>Target: {ms.targetDate}</time>
              {ms.completedDate ? (
                <time dateTime={ms.completedDate}>Completed: {ms.completedDate}</time>
              ) : null}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
