'use client';

import './creative-studio-carousel-dots.css';

export type CarouselDotsSize = 'sm' | 'md';

export type CarouselDotsProps = {
  /** Number of slides / dots. Prefer this over `length`. */
  count?: number;
  /** Alias for `count` (same meaning). */
  length?: number;
  activeIndex: number;
  onSelect: (index: number) => void;
  /** Fallback aria-label for the group; individual dots use getLabel when provided. */
  ariaLabel?: string;
  /** Per-dot accessible name. Defaults to "Slide {n}". */
  getLabel?: (index: number) => string;
  className?: string;
  size?: CarouselDotsSize;
};

/**
 * Shared Creative Studio carousel pagination dots.
 * Reusable by Website, Landing Page, Blog, Email, Proposal, Presentation builders.
 */
export function CarouselDots({
  count: countProp,
  length,
  activeIndex,
  onSelect,
  ariaLabel = 'Carousel pagination',
  getLabel,
  className,
  size = 'md',
}: CarouselDotsProps) {
  const count = countProp ?? length ?? 0;
  if (count <= 0) return null;

  const safeActive = ((activeIndex % count) + count) % count;

  return (
    <div
      className={`cs-carousel-dots cs-carousel-dots--${size}${className ? ` ${className}` : ''}`}
      role="tablist"
      aria-label={ariaLabel}
      data-testid="cs-carousel-dots"
    >
      {Array.from({ length: count }, (_, idx) => (
        <button
          key={idx}
          type="button"
          role="tab"
          aria-selected={safeActive === idx}
          className={`cs-carousel-dots__dot${safeActive === idx ? ' is-active' : ''}`}
          aria-label={getLabel?.(idx) ?? `Slide ${idx + 1}`}
          onClick={(e) => {
            e.stopPropagation();
            onSelect(idx);
          }}
        />
      ))}
    </div>
  );
}
