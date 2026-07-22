'use client';

import { useTranslations } from 'next-intl';

import { useGlobalSearch } from '@/lib/search/global-search-context';

export function GlobalSearchEntry({
  title,
  hint,
  cta,
  unavailable,
}: {
  title: string;
  hint: string;
  cta: string;
  unavailable: string;
}) {
  const tSearch = useTranslations('search');
  const { canSearch, openPalette } = useGlobalSearch();
  const isMac =
    typeof navigator !== 'undefined' && navigator.platform.toLowerCase().includes('mac');
  const shortcut = isMac ? '⌘K' : 'Ctrl+K';

  return (
    <section className="ecc-search" aria-label={title}>
      <div className="ecc-search__copy">
        <h2 className="ecc-section-title">{title}</h2>
        <p className="ecc-section-hint">{hint}</p>
        <p className="ecc-search__entities">{tSearch('hint')}</p>
      </div>
      {canSearch ? (
        <button type="button" className="ecc-search__button" onClick={openPalette}>
          <span>{cta}</span>
          <kbd>{shortcut}</kbd>
        </button>
      ) : (
        <p className="leads__state">{unavailable}</p>
      )}
    </section>
  );
}