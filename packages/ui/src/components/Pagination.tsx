import type { ReactNode } from 'react';

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPrevious: () => void;
  onNext: () => void;
  previousLabel: string;
  nextLabel: string;
  summary?: ReactNode;
  className?: string;
}

export function Pagination({
  page,
  pageSize,
  total,
  onPrevious,
  onNext,
  previousLabel,
  nextLabel,
  summary,
  className,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canPrevious = page > 1;
  const canNext = page < totalPages;

  return (
    <nav className={`ih-pagination${className ? ` ${className}` : ''}`} aria-label="Pagination">
      {summary ? <div className="ih-pagination__summary">{summary}</div> : null}
      <div className="ih-pagination__actions">
        <button type="button" className="ih-btn ih-btn--secondary" disabled={!canPrevious} onClick={onPrevious}>
          {previousLabel}
        </button>
        <button type="button" className="ih-btn ih-btn--secondary" disabled={!canNext} onClick={onNext}>
          {nextLabel}
        </button>
      </div>
    </nav>
  );
}
