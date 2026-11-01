'use client';

import { useTranslations } from 'next-intl';

import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { SectionHeader } from '../section-header';

const ROLE_LABELS: Record<string, string> = {
  investor_relations: 'Investor Relations',
  project_manager: 'Project Manager',
  asset_manager: 'Asset Manager',
  legal: 'Legal',
  accounting: 'Accounting',
};

export interface ContactsSectionProps {
  detail: InvestmentDetail;
  onPlaceholderAction: (message: string) => void;
}

export function ContactsSection({ detail, onPlaceholderAction }: ContactsSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const { contacts } = detail;

  return (
    <section className="inv-detail-panel" aria-labelledby="contacts-heading">
      <SectionHeader title={tChrome('k13b24f9c83')} subtitle={tChrome('kea02aeba67')} />

      <div className="inv-detail-contacts" role="list">
        {contacts.map((contact) => (
          <article key={contact.id} className="inv-detail-contacts__card" role="listitem">
            <div className="inv-detail-contacts__avatar" aria-hidden="true">
              {contact.name
                .split(' ')
                .map((n) => n[0])
                .join('')}
            </div>
            <div className="inv-detail-contacts__info">
              <h3 className="inv-detail-contacts__name">{contact.name}</h3>
              <p className="inv-detail-contacts__role">{ROLE_LABELS[contact.role] ?? contact.role}</p>
              <p className="inv-detail-contacts__title">{contact.title}</p>
              <dl className="inv-detail-contacts__details">
                <div>
                  <dt>{tChrome('k84add5b295')}</dt>
                  <dd>
                    <a href={`mailto:${contact.email}`}>{contact.email}</a>
                  </dd>
                </div>
                <div>
                  <dt>{tChrome('k77064d5265')}</dt>
                  <dd>
                    <a href={`tel:${contact.phone.replace(/\D/g, '')}`}>{contact.phone}</a>
                  </dd>
                </div>
                <div>
                  <dt>{tChrome('k681b5b5ae1')}</dt>
                  <dd>{contact.availability}</dd>
                </div>
              </dl>
            </div>
            <div className="inv-detail-contacts__actions">
              <button
                type="button"
                className="investor-header__action-btn"
                onClick={() => onPlaceholderAction(`Message to ${contact.name} coming soon.`)}
              >
                Send Message
              </button>
              <button
                type="button"
                className="investor-header__action-btn investor-header__action-btn--primary"
                onClick={() => onPlaceholderAction(`Schedule call with ${contact.name} coming soon.`)}
              >
                Schedule Call
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
