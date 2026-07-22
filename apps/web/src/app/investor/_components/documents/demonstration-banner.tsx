import { DEMONSTRATION_DISCLAIMER } from '../../_data/document-types';

export function DemonstrationBanner({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`inv-docs__demo-banner${compact ? ' inv-docs__demo-banner--compact' : ''}`}
      role="note"
      aria-label={DEMONSTRATION_DISCLAIMER}
    >
      <span className="inv-docs__demo-banner-icon" aria-hidden="true">
        ⚠
      </span>
      <div>
        <strong>{DEMONSTRATION_DISCLAIMER}</strong>
        {!compact ? (
          <p>
            All signatures, certificates, and document actions in this workspace are simulated
            for demonstration purposes only. No legally binding agreements are created.
          </p>
        ) : null}
      </div>
    </div>
  );
}
