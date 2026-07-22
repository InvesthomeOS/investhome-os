import type { ReactNode } from 'react';

export interface SectionHeaderProps {
  title: string;
  description?: string;
  badge?: string;
  actions?: ReactNode;
  className?: string;
}

export function SectionHeader({ title, description, badge, actions, className }: SectionHeaderProps) {
  return (
    <div className={`ih-section-header ds-section-header${className ? ` ${className}` : ''}`}>
      <div className="ih-section-header__title-row ds-section-header__title-row">
        <div>
          <h2 className="ih-section-header__title ds-section-header__title">{title}</h2>
          {description ? <p className="ds-type-body-small">{description}</p> : null}
        </div>
        {badge ? <span className="ih-section-header__badge">{badge}</span> : null}
      </div>
      {actions ? (
        <div className="ih-section-header__actions ds-section-header__actions">{actions}</div>
      ) : null}
    </div>
  );
}
