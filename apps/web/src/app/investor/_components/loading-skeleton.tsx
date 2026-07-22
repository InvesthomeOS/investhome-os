export interface LoadingSkeletonProps {
  variant?: 'text' | 'title' | 'card';
  count?: number;
  className?: string;
}

export function LoadingSkeleton({
  variant = 'text',
  count = 1,
  className,
}: LoadingSkeletonProps) {
  const items = Array.from({ length: count }, (_, i) => i);

  return (
    <>
      {items.map((i) => (
        <div
          key={i}
          className={`inv-skeleton inv-skeleton--${variant}${className ? ` ${className}` : ''}`}
          aria-hidden="true"
        />
      ))}
    </>
  );
}

export function LoadingSkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="inv-dashboard__kpi-grid">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="inv-skeleton inv-skeleton--card" aria-hidden="true" />
      ))}
    </div>
  );
}
