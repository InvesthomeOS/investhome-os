'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { BrandLogo } from '@/components/brand/brand-logo';

export function SiteFooter() {
  const t = useTranslations('site.footer');

  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="site-footer__brand">
          <BrandLogo tone="color" layout="full" className="site-footer__logo" />
          <p>{t('tagline')}</p>
        </div>

        <div className="site-footer__cols">
          <div>
            <h2>{t('explore')}</h2>
            <Link href="/projects">{t('projects')}</Link>
            <Link href="/calculators">{t('calculators')}</Link>
            <Link href="/insights">{t('insights')}</Link>
            <Link href="/workflow">{t('workflow')}</Link>
          </div>
          <div>
            <h2>{t('invest')}</h2>
            <Link href="/lead/consultation">{t('consultation')}</Link>
            <Link href="/lead/analysis">{t('analysis')}</Link>
            <Link href="/lead/brochure">{t('brochure')}</Link>
            <Link href="/lead/meeting">{t('meeting')}</Link>
          </div>
          <div>
            <h2>{t('company')}</h2>
            <Link href="/contact">{t('contact')}</Link>
            <Link href="/lead/newsletter">{t('newsletter')}</Link>
            <Link href="/lead/guide">{t('guide')}</Link>
            <Link href="/login">{t('platform')}</Link>
          </div>
        </div>
      </div>
      <div className="site-footer__bar">
        <span>© {new Date().getFullYear()} Investhome</span>
        <span>{t('disclaimer')}</span>
      </div>
    </footer>
  );
}
