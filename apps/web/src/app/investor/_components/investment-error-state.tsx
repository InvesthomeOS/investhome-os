export interface InvestmentErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export function InvestmentErrorState({
  title = 'Unable to load investments',
  description = 'We could not retrieve your investment data. Please try again later.',
  onRetry,
}: InvestmentErrorStateProps) {
  return (
    <div className="inv-investments__error" role="alert">
      <span className="inv-investments__error-icon" aria-hidden="true">
        !
      </span>
      <h3 className="inv-investments__error-title">{title}</h3>
      <p className="inv-investments__error-description">{description}</p>
      {onRetry ? (
        <button type="button" className="inv-empty-state__action" onClick={onRetry}>
          Try Again
        </button>
      ) : null}
    </div>
  );
}
