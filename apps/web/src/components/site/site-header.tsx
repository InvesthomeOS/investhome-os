'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import { useState } from 'react';

import { BrandLogo } from '@/components/brand/brand-logo';
import { writeLocaleCookie } from '@/lib/i18n/locale-cookie';
import type { AppLocale } from '@/i18n/config';

const NAV: { href: Route; key: 'projects' | 'calculators' | 'insights' | 'contact' }[] = [
  { href: '/projects', key: 'projects' },
  { href: '/calculators', key: 'calculators' },
  { href: '/insights', key: 'insights' },
  { href: '/contact', key: 'contact' },
];

export function SiteHeader() {
  const t = useTranslations('site.nav');
  const locale = useLocale();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const switchLocale = (next: AppLocale) => {
    writeLocaleCookie(next);
    window.location.reload();
  };

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link href="/" className="site-header__brand" aria-label="Investhome">
          <BrandLogo tone="color" layout="full" className="site-header__logo" priority />
        </Link>

        <nav className="site-header__nav" aria-label={t('primary')}>
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? 'site-header__link is-active' : 'site-header__link'}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </nav>

        <div className="site-header__actions">
          <div className="site-header__locale" role="group" aria-label={t('language')}>
            <button
              type="button"
              className={locale === 'tr' ? 'is-active' : undefined}
              onClick={() => switchLocale('tr')}
            >
              TR
            </button>
            <button
              type="button"
              className={locale === 'en' ? 'is-active' : undefined}
              onClick={() => switchLocale('en')}
            >
              EN
            </button>
          </div>
          <Link href={'/lead/consultation' as Route} className="site-btn site-btn--primary site-btn--sm">
            {t('cta')}
          </Link>
          <Link href="/login" className="site-header__login">
            {t('login')}
          </Link>
          <button
            type="button"
            className="site-header__menu"
            aria-expanded={open}
            aria-controls="site-mobile-nav"
            onClick={() => setOpen((v) => !v)}
          >
            <span className="sr-only">{t('menu')}</span>
            <span aria-hidden />
            <span aria-hidden />
          </button>
        </div>
      </div>

      {open ? (
        <div id="site-mobile-nav" className="site-header__drawer">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
              {t(item.key)}
            </Link>
          ))}
          <Link href={'/lead/consultation' as Route} onClick={() => setOpen(false)}>
            {t('cta')}
          </Link>
        </div>
      ) : null}
    </header>
  );
}
