'use client';

import { useTranslations } from 'next-intl';

import { useGlobalSearch } from '@/lib/search/global-search-context';

export function GlobalSearchTrigger() {
  const t = useTranslations('search');
  const { canSearch, openPalette } = useGlobalSearch();

  if (!canSearch) return null;

  const isMac = typeof navigator !== 'undefined' && navigator.platform.toLowerCase().includes('mac');
  const shortcut = isMac ? '⌘K' : 'Ctrl+K';

  return (
    <button type="button" className="global-search-trigger" onClick={openPalette}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5" />
        <path d="M20 20 16.5 16.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <span className="global-search-trigger__label">{t('placeholder')}</span>
      <kbd className="global-search-trigger__kbd">{shortcut}</kbd>
    </button>
  );
}
