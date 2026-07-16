import type { ReactNode } from 'react';

export interface SectionHeaderProps {
  title: string;
  badge?: string;
  actions?: ReactNode;
  className?: string;
}

export function SectionHeader({ title, badge, actions, className }: SectionHeaderProps) {
  return (
    <div className={`ih-section-header${className ? ` ${className}` : ''}`}>
      <div className="ih-section-header__title-row">
        <h2 className="ih-section-header__title">{title}</h2>
        {badge ? <span className="ih-section-header__badge">{badge}</span> : null}
      </div>
      {actions ? <div className="ih-section-header__actions">{actions}</div> : null}
    </div>
  );
}
