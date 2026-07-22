export interface LoadingStateProps {
  label?: string;
  /** Prefer skeleton layout over spinner text for content regions */
  variant?: 'text' | 'skeleton';
  lines?: number;
}

export function LoadingState({ label = 'Loading…', variant = 'skeleton', lines = 4 }: LoadingStateProps) {
  if (variant === 'skeleton') {
    const count = Math.max(2, Math.min(lines, 8));
    return (
      <div className="ih-loading-skeleton ih-skeleton-block" role="status" aria-busy="true" aria-label={label}>
        <div className="ih-skeleton-block__line ih-skeleton-block__line--title" />
        {Array.from({ length: count }, (_, index) => (
          <div
            key={index}
            className={`ih-skeleton-block__line${index === count - 1 ? ' ih-skeleton-block__line--short' : ' ih-skeleton-block__line--full'}`}
          />
        ))}
        <span className="sr-only">{label}</span>
      </div>
    );
  }

  return (
    <p className="dashboard__loading" role="status" aria-busy="true">
      {label}
    </p>
  );
}
