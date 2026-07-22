import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';
import { MilestoneTimeline } from './milestone-timeline';

const TIMELINE_STATUS_LABELS: Record<
  InvestmentDetail['progress']['timelineStatus'],
  string
> = {
  on_track: 'On Track',
  ahead: 'Ahead of Schedule',
  behind: 'Behind Schedule',
  at_risk: 'At Risk',
};

export interface ProjectProgressSectionProps {
  detail: InvestmentDetail;
}

export function ProjectProgressSection({ detail }: ProjectProgressSectionProps) {
  const { progress, milestones, investment: inv } = detail;

  const bars = [
    { label: 'Construction', percent: progress.constructionPercent },
    { label: 'Leasing', percent: progress.leasingPercent },
    { label: 'Sales', percent: progress.salesPercent },
  ];

  return (
    <div className="inv-detail-progress">
      <section className="inv-detail-panel" aria-labelledby="progress-heading">
        <SectionHeader
          title="Project Progress"
          subtitle={`${progress.overallPercent}% complete · ${TIMELINE_STATUS_LABELS[progress.timelineStatus]}`}
        />

        <div className="inv-detail-progress__summary">
          <div className="inv-detail-progress__overall">
            <div
              className="inv-detail-progress__ring"
              role="progressbar"
              aria-valuenow={progress.overallPercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Overall project progress"
            >
              <svg viewBox="0 0 100 100" aria-hidden="true">
                <circle cx="50" cy="50" r="42" fill="none" stroke="var(--inv-border)" strokeWidth="6" />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  stroke="var(--inv-gold)"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={`${(progress.overallPercent / 100) * 264} 264`}
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <span className="inv-detail-progress__ring-value">{progress.overallPercent}%</span>
            </div>
            <div>
              <p className="inv-detail-progress__phase">Current Phase: {progress.currentPhase}</p>
              <p className="inv-detail-progress__timeline">
                Timeline: {TIMELINE_STATUS_LABELS[progress.timelineStatus]}
              </p>
              <p className="inv-detail-progress__completion">
                Est. Completion: {progress.estimatedCompletion} · {progress.daysRemaining} days remaining
              </p>
            </div>
          </div>

          <div className="inv-detail-progress__bars">
            {bars.map((bar) => (
              <div key={bar.label} className="inv-detail-progress__bar-item">
                <div className="inv-detail-progress__bar-header">
                  <span>{bar.label}</span>
                  <span>{bar.percent}%</span>
                </div>
                <div className="inv-detail-progress__bar-track">
                  <div
                    className="inv-detail-progress__bar-fill"
                    style={{ width: `${bar.percent}%` }}
                    role="progressbar"
                    aria-valuenow={bar.percent}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`${bar.label} progress`}
                  />
                </div>
              </div>
            ))}
          </div>

          <dl className="inv-detail-progress__budget">
            <div>
              <dt>Budget Spent</dt>
              <dd>{formatInvestorCurrency(progress.budgetSpent, inv.currency)}</dd>
            </div>
            <div>
              <dt>Total Budget</dt>
              <dd>{formatInvestorCurrency(progress.totalBudget, inv.currency)}</dd>
            </div>
            <div>
              <dt>Budget Utilization</dt>
              <dd>{progress.budgetSpentPercent}%</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="inv-detail-panel" aria-labelledby="milestones-heading">
        <SectionHeader title="Milestone Timeline" subtitle={`${milestones.length} milestones tracked`} />
        <MilestoneTimeline milestones={milestones} />
      </section>
    </div>
  );
}
