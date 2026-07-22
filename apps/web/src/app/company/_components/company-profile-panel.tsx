'use client';

import { Button, EmptyState, LoadingState, Tabs } from '@investhome/ui';
import { useTranslations } from 'next-intl';
import { useState } from 'react';

import type { CompanyRecord } from '@/lib/api/companies';

type CompanyProfilePanelProps = {
  company: CompanyRecord | null;
  loading?: boolean;
  onEdit?: () => void;
  canEdit?: boolean;
};

export function CompanyProfilePanel({ company, loading, onEdit, canEdit }: CompanyProfilePanelProps) {
  const t = useTranslations('company.companies');
  const [activeTab, setActiveTab] = useState('general');

  if (loading) {
    return <LoadingState label={t('loadingProfile')} />;
  }

  if (!company) {
    return <EmptyState title={t('selectCompany')} description={t('selectCompanyHint')} />;
  }

  const tabItems = [
    { id: 'general', label: t('tabs.general') },
    { id: 'legal', label: t('tabs.legal') },
    { id: 'addresses', label: t('tabs.addresses') },
    { id: 'contacts', label: t('tabs.contacts') },
    { id: 'bankAccounts', label: t('tabs.bankAccounts') },
    { id: 'documents', label: t('tabs.documents') },
    { id: 'related', label: t('tabs.related') },
    { id: 'notes', label: t('tabs.notes') },
  ];

  const tabContent = (() => {
    switch (activeTab) {
      case 'legal':
        return (
          <dl className="company-profile__grid">
            <div><dt>{t('fields.registrationNumber')}</dt><dd>{company.registration_number ?? '—'}</dd></div>
            <div><dt>{t('fields.taxId')}</dt><dd>{company.tax_id ?? '—'}</dd></div>
            <div><dt>{t('fields.country')}</dt><dd>{company.country ?? '—'}</dd></div>
            <div><dt>{t('fields.state')}</dt><dd>{company.state ?? '—'}</dd></div>
            <div><dt>{t('fields.city')}</dt><dd>{company.city ?? '—'}</dd></div>
          </dl>
        );
      case 'addresses':
        return company.addresses.length === 0 ? (
          <EmptyState title={t('empty.addresses')} />
        ) : (
          <ul className="company-profile__list">
            {company.addresses.map((address) => (
              <li key={address.id}>
                <strong>{address.address_type}</strong>
                <span>{[address.address_line_1, address.city, address.country].filter(Boolean).join(', ') || '—'}</span>
              </li>
            ))}
          </ul>
        );
      case 'contacts':
        return company.contacts.length === 0 ? (
          <EmptyState title={t('empty.contacts')} />
        ) : (
          <ul className="company-profile__list">
            {company.contacts.map((contact) => (
              <li key={contact.id}>
                <strong>{contact.full_name}</strong>
                <span>{contact.role}{contact.is_signatory ? ` · ${t('signatory')}` : ''}</span>
              </li>
            ))}
          </ul>
        );
      case 'bankAccounts':
        return company.bank_accounts.length === 0 ? (
          <EmptyState title={t('empty.bankAccounts')} />
        ) : (
          <ul className="company-profile__list">
            {company.bank_accounts.map((account) => (
              <li key={account.id}>
                <strong>{account.bank_name}</strong>
                <span>{account.account_number ?? account.iban ?? '—'}</span>
              </li>
            ))}
          </ul>
        );
      case 'documents':
        return company.documents.length === 0 ? (
          <EmptyState title={t('empty.documents')} />
        ) : (
          <ul className="company-profile__list">
            {company.documents.map((document) => (
              <li key={document.id}>
                <strong>{document.title}</strong>
                <span>{document.reference_code ?? '—'}</span>
              </li>
            ))}
          </ul>
        );
      case 'related':
        return company.relationships.length === 0 ? (
          <EmptyState title={t('empty.related')} />
        ) : (
          <ul className="company-profile__list">
            {company.relationships.map((relationship) => (
              <li key={relationship.id}>
                <strong>{relationship.related_company_name ?? relationship.related_company_id}</strong>
                <span>{relationship.relationship_type}</span>
              </li>
            ))}
          </ul>
        );
      case 'notes':
        return <p className="company-profile__notes">{company.notes ?? t('empty.notes')}</p>;
      default:
        return (
          <dl className="company-profile__grid">
            <div><dt>{t('fields.companyName')}</dt><dd>{company.company_name}</dd></div>
            <div><dt>{t('fields.legalName')}</dt><dd>{company.legal_name ?? '—'}</dd></div>
            <div><dt>{t('fields.entityType')}</dt><dd>{t(`entityTypes.${company.entity_type}` as 'entityTypes.other')}</dd></div>
            <div><dt>{t('fields.status')}</dt><dd>{t(`statuses.${company.status}` as 'statuses.draft')}</dd></div>
            <div><dt>{t('fields.industry')}</dt><dd>{company.industry ?? '—'}</dd></div>
            <div><dt>{t('fields.owner')}</dt><dd>{company.owner_name ?? '—'}</dd></div>
            <div><dt>{t('fields.employees')}</dt><dd>{company.employee_count}</dd></div>
            <div><dt>{t('fields.branches')}</dt><dd>{company.branch_count}</dd></div>
          </dl>
        );
    }
  })();

  return (
    <section className="company-profile">
      <header className="company-profile__header">
        <div>
          <h2>{company.company_name}</h2>
          <p>{company.legal_name ?? t('noLegalName')}</p>
        </div>
        {canEdit && onEdit ? (
          <Button type="button" variant="secondary" onClick={onEdit}>
            {t('actions.edit')}
          </Button>
        ) : null}
      </header>
      <Tabs tabs={tabItems} activeId={activeTab} onChange={setActiveTab} />
      <div className="company-profile__content">{tabContent}</div>
    </section>
  );
}
