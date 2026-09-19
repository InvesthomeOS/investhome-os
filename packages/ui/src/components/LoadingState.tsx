export interface LoadingStateProps {
  label?: string;
  variant?: 'text' | 'skeleton';
  lines?: number;
}

export function LoadingState({ label = 'Loading…', variant = 'text', lines = 4 }: LoadingStateProps) {
  if (variant === 'skeleton') {
    const count = Math.max(2, Math.min(lines, 8));
    return (
      <div className="ih-loading-skeleton" role="status" aria-busy="true" aria-label={label}>
        {Array.from({ length: count }, (_, index) => (
          <div key={index} className="ih-loading-skeleton__line" />
        ))}
        <span className="sr-only">{label}</span>
      </div>
    );
  }
  return <p className="dashboard__loading">{label}</p>;
}
