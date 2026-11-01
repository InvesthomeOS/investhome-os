'use client';

import { useTranslations } from 'next-intl';

import { EmptyState } from '../_components/empty-state';
import { SectionHeader } from '../_components/section-header';

const SETTINGS_SECTIONS = [
  { id: 'notifications', title: 'Notification Preferences', description: 'Email and in-app alert settings' },
  { id: 'security', title: 'Security', description: 'Password, two-factor authentication' },
  { id: 'statements', title: 'Statement Delivery', description: 'Monthly and quarterly report preferences' },
  { id: 'privacy', title: 'Privacy', description: 'Data sharing and communication preferences' },
];

export default function SettingsPage() {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <div className="investor-page">
      <h1 className="investor-page__title">{tChrome('kc7f73bb54d')}</h1>
      <p className="investor-page__subtitle">{tChrome('k26bc549293')}</p>

      <SectionHeader title={tChrome('k9dfd349ebe')} subtitle={tChrome('kaf36fc7dc8')} />

      <div style={{ display: 'grid', gap: '1rem', maxWidth: '40rem' }}>
        {SETTINGS_SECTIONS.map((section) => (
          <article key={section.id} className="inv-metric-card" style={{ padding: '1.25rem' }}>
            <h3 className="inv-metric-card__title">{section.title}</h3>
            <p className="inv-section-header__subtitle">{section.description}</p>
          </article>
        ))}
      </div>

      <div style={{ marginTop: '2rem' }}>
        <EmptyState
          icon="⚙"
          title={tChrome('kadd2c9538f')}
          description="Preference controls will be wired to backend services in a future release. This module uses mock data only."
        />
      </div>
    </div>
  );
}
