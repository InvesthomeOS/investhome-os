import type { ReactNode } from 'react';

export type PipelineStageTone =
  | 'lead'
  | 'qualify'
  | 'proposal'
  | 'negotiation'
  | 'won'
  | 'lost'
  | 'neutral';

export interface PipelineColumnProps {
  title: string;
  count?: number;
  tone?: PipelineStageTone;
  children?: ReactNode;
  headerAction?: ReactNode;
  className?: string;
}

/**
 * Kanban stage column with subtle tint (UXR1 V2 §06).
 * Cards inside should use Card / deal-card hierarchy with clear separation.
 */
export function PipelineColumn({
  title,
  count,
  tone = 'neutral',
  children,
  headerAction,
  className,
}: PipelineColumnProps) {
  const classes = [
    'ds-pipeline-column',
    `ds-pipeline-column--${tone}`,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <section className={classes} aria-label={`${title} column`}>
      <header className="ds-pipeline-column__header">
        <div className="ds-pipeline-column__title-block">
          <h3 className="ds-pipeline-column__title">{title}</h3>
          {typeof count === 'number' ? (
            <span className="ds-pipeline-column__count">{count}</span>
          ) : null}
        </div>
        {headerAction}
      </header>
      <div className="ds-pipeline-column__body">{children}</div>
    </section>
  );
}
