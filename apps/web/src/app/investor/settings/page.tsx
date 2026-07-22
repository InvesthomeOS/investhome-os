'use client';

import { EmptyState } from '../_components/empty-state';
import { SectionHeader } from '../_components/section-header';

const SETTINGS_SECTIONS = [
  { id: 'notifications', title: 'Notification Preferences', description: 'Email and in-app alert settings' },
  { id: 'security', title: 'Security', description: 'Password, two-factor authentication' },
  { id: 'statements', title: 'Statement Delivery', description: 'Monthly and quarterly report preferences' },
  { id: 'privacy', title: 'Privacy', description: 'Data sharing and communication preferences' },
];

export default function SettingsPage() {
  return (
    <div className="investor-page">
      <h1 className="investor-page__title">Settings</h1>
      <p className="investor-page__subtitle">Manage your investor workspace preferences.</p>

      <SectionHeader title="Preferences" subtitle="Configure your account settings" />

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
          title="Settings are UI-only"
          description="Preference controls will be wired to backend services in a future release. This module uses mock data only."
        />
      </div>
    </div>
  );
}
