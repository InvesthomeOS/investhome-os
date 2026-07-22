'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import { writeLocaleCookie } from '@/lib/i18n/locale-cookie';
import type { AppLocale } from '@/i18n/config';

import { usePortalSession } from '../_state/portal-session';

export function PortalHeader() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const router = useRouter();
  const { profile, logout } = usePortalSession();

  function switchLocale(next: AppLocale) {
    writeLocaleCookie(next);
    router.refresh();
  }

  return (
    <header className="app-header portal-header" data-testid="portal-header">
      <div className="app-header__left">
        <div>
          <strong style={{ letterSpacing: '-0.02em' }}>{t('brand')}</strong>
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{t('secureNote')}</div>
        </div>
      </div>
      <div className="app-header__right portal-header-actions">
        <div className="portal-lang" data-testid="portal-lang">
          <button
            type="button"
            aria-pressed={locale === 'tr'}
            onClick={() => switchLocale('tr')}
          >
            TR
          </button>
          <button
            type="button"
            aria-pressed={locale === 'en'}
            onClick={() => switchLocale('en')}
          >
            EN
          </button>
        </div>
        <span style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>
          {profile?.fullName ?? '—'}
        </span>
        <button type="button" className="portal-btn" onClick={() => void logout()}>
          {t('header.logout')}
        </button>
      </div>
    </header>
  );
}
