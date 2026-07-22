export interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function SectionHeader({ title, subtitle, actionLabel, onAction }: SectionHeaderProps) {
  return (
    <div className="inv-section-header">
      <div>
        <h2 className="inv-section-header__title">{title}</h2>
        {subtitle ? <p className="inv-section-header__subtitle">{subtitle}</p> : null}
      </div>
      {actionLabel && onAction ? (
        <button type="button" className="inv-section-header__action" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
