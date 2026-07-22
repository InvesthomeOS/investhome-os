'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';

import '@/components/adoption/adoption-g13.css';

const TOPICS = [
  {
    id: 'login',
    en: 'Sign in securely',
    tr: 'Güvenli giriş',
    bodyEn: 'Use your portal email and password. Enable MFA when prompted for stronger protection.',
    bodyTr: 'Portal e-posta ve şifrenizi kullanın. Daha güçlü koruma için MFA istendiğinde etkinleştirin.',
  },
  {
    id: 'portfolio',
    en: 'Your portfolio',
    tr: 'Portföyünüz',
    bodyEn: 'See projects linked to you, progress updates, and shared documents in one place.',
    bodyTr: 'Size bağlı projeleri, ilerleme güncellemelerini ve paylaşılan belgeleri tek yerde görün.',
  },
  {
    id: 'payments',
    en: 'Payments',
    tr: 'Ödemeler',
    bodyEn: 'Track upcoming and completed payments. Contact your relationship manager for questions.',
    bodyTr: 'Yaklaşan ve tamamlanan ödemeleri takip edin. Sorularınız için ilişki yöneticinize yazın.',
  },
  {
    id: 'documents',
    en: 'Documents',
    tr: 'Belgeler',
    bodyEn: 'Download agreements and reports shared with you. Some files may require review before release.',
    bodyTr: 'Sizinle paylaşılan sözleşmeleri ve raporları indirin. Bazı dosyalar paylaşım öncesi inceleme gerektirebilir.',
  },
  {
    id: 'messages',
    en: 'Messages & notifications',
    tr: 'Mesajlar ve bildirimler',
    bodyEn: 'Stay informed about meetings, documents, and payment reminders.',
    bodyTr: 'Toplantılar, belgeler ve ödeme hatırlatmaları hakkında bilgi alın.',
  },
  {
    id: 'security',
    en: 'Account security',
    tr: 'Hesap güvenliği',
    bodyEn: 'Update your password regularly and keep MFA enabled on shared devices.',
    bodyTr: 'Şifrenizi düzenli güncelleyin ve paylaşılan cihazlarda MFA’yı açık tutun.',
  },
] as const;

export default function PortalHelpPage() {
  const locale = useLocale();
  const t = useTranslations('portalG9');

  return (
    <div className="portal-page adop-g13" data-testid="portal-help" data-tour="portal-help-root" style={{ border: 0, minHeight: 'auto', background: 'transparent', boxShadow: 'none' }}>
      <header className="adop-g13__top" style={{ borderRadius: 12, marginBottom: '1rem' }}>
        <div>
          <p className="adop-g13__eyebrow">{locale === 'en' ? 'Investor help' : 'Yatırımcı yardımı'}</p>
          <h1 className="adop-g13__title">
            {locale === 'en' ? 'How can we help?' : 'Size nasıl yardımcı olabiliriz?'}
          </h1>
          <p className="adop-g13__subtitle">
            {locale === 'en'
              ? 'Clear guidance for your portal — no internal system jargon.'
              : 'Portalınız için net rehberlik — dahili sistem jargonu yok.'}
          </p>
        </div>
        <div className="adop-g13__top-actions">
          <Link href={'/portal/support' as Route} className="adop-g13__btn adop-g13__btn--primary">
            {t('nav.support')}
          </Link>
        </div>
      </header>

      <div className="adop-g13__grid">
        {TOPICS.map((topic) => (
          <section key={topic.id} className="adop-g13__panel adop-g13__panel--6" data-testid={`portal-help-${topic.id}`}>
            <h2 className="adop-g13__panel-title">{locale === 'en' ? topic.en : topic.tr}</h2>
            <p className="adop-g13__muted">{locale === 'en' ? topic.bodyEn : topic.bodyTr}</p>
          </section>
        ))}
      </div>
    </div>
  );
}
