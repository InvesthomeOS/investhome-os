import type { ReactNode } from 'react';

export interface UnitCardBadge {
  label: string;
  tone?: 'discount' | 'ai' | 'status' | 'info';
}

export interface UnitCardProps {
  unitCode: string;
  beds: number | string;
  baths: number | string;
  sqft: number | string;
  price: string;
  estimatedRent?: string;
  imageUrl?: string;
  imageAlt?: string;
  badges?: UnitCardBadge[];
  /** Slot for future AI / insight badges without layout rewrite */
  aiBadges?: ReactNode;
  footer?: ReactNode;
  onClick?: () => void;
  className?: string;
  href?: string;
}

const BADGE_TONE: Record<NonNullable<UnitCardBadge['tone']>, string> = {
  discount: 'ds-unit-card__badge--discount',
  ai: 'ds-unit-card__badge--ai',
  status: 'ds-unit-card__badge--status',
  info: 'ds-unit-card__badge--info',
};

/**
 * Portrait inventory unit card (UXR1 V2 §07).
 * Fields: Unit Code, Beds, Baths, Sqft, Price, Estimated Rent, Discount Badge.
 * `aiBadges` is the extension point for future AI badges.
 */
export function UnitCard({
  unitCode,
  beds,
  baths,
  sqft,
  price,
  estimatedRent,
  imageUrl,
  imageAlt,
  badges,
  aiBadges,
  footer,
  onClick,
  className,
  href,
}: UnitCardProps) {
  const classes = ['ds-unit-card', className].filter(Boolean).join(' ');
  const body = (
    <>
      <div className="ds-unit-card__media">
        {imageUrl ? (
          <img src={imageUrl} alt={imageAlt ?? unitCode} className="ds-unit-card__image" />
        ) : (
          <div className="ds-unit-card__image-placeholder" aria-hidden />
        )}
        <div className="ds-unit-card__badge-row">
          {badges?.map((b) => (
            <span
              key={b.label}
              className={`ds-unit-card__badge ${BADGE_TONE[b.tone ?? 'info']}`}
            >
              {b.label}
            </span>
          ))}
          {aiBadges}
        </div>
      </div>
      <div className="ds-unit-card__body">
        <div className="ds-unit-card__code">{unitCode}</div>
        <dl className="ds-unit-card__specs">
          <div>
            <dt>Beds</dt>
            <dd>{beds}</dd>
          </div>
          <div>
            <dt>Baths</dt>
            <dd>{baths}</dd>
          </div>
          <div>
            <dt>Sqft</dt>
            <dd>{sqft}</dd>
          </div>
        </dl>
        <div className="ds-unit-card__price">{price}</div>
        {estimatedRent ? (
          <div className="ds-unit-card__rent">Est. rent {estimatedRent}</div>
        ) : null}
        {footer}
      </div>
    </>
  );

  if (href) {
    return (
      <a className={classes} href={href} onClick={onClick}>
        {body}
      </a>
    );
  }

  return (
    <article className={classes} onClick={onClick} role={onClick ? 'button' : undefined}>
      {body}
    </article>
  );
}
