'use client';

import { formatInvestorDate, investorProfile } from '../_data/mock-data';
import { SectionHeader } from '../_components/section-header';

export default function ProfilePage() {
  return (
    <div className="investor-page">
      <h1 className="investor-page__title">Profile</h1>
      <p className="investor-page__subtitle">Your investor account details and membership.</p>

      <div className="inv-dashboard__panel" style={{ maxWidth: '36rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: '1.5rem' }}>
          <span
            className="investor-header__avatar-circle"
            style={{ width: '4rem', height: '4rem', fontSize: '1.25rem' }}
            aria-hidden="true"
          >
            {investorProfile.avatarInitials}
          </span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>{investorProfile.name}</h2>
            <span className="investor-sidebar__tier-badge" style={{ marginTop: '0.5rem' }}>
              {investorProfile.investorTier} Investor
            </span>
          </div>
        </div>

        <SectionHeader title="Account Details" />

        <dl style={{ margin: 0, display: 'grid', gap: '1rem' }}>
          {[
            { label: 'Email', value: investorProfile.email },
            { label: 'Phone', value: investorProfile.phone },
            { label: 'Member Since', value: formatInvestorDate(investorProfile.memberSince) },
            { label: 'Investor ID', value: investorProfile.id },
          ].map((field) => (
            <div key={field.label}>
              <dt style={{ fontSize: '0.75rem', color: 'var(--inv-text-muted)', marginBottom: '0.25rem' }}>
                {field.label}
              </dt>
              <dd style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 500 }}>{field.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
