'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, TextArea } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { fetchDocumentsByEntity } from '@/lib/api/documents';
import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  crmCompaniesMutations,
  crmCompaniesQueries,
  crmCompaniesQueryKeys,
} from '@/lib/query/crm-companies-queries';
import { fetchCrmCompanyTimeline, transferCrmCompanyOwnership } from '@/workspaces/crm/api/companies';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { DocumentGallery } from '@/workspaces/crm/contact-card/document-gallery';

import '@/workspaces/crm/contact-card/contact-card.css';
import '../companies/companies-ops.css';

const COMPANY_TYPE_KEYS = new Set([
  'investment_company',
  'buyer_entity',
  'brokerage',
  'law_firm',
  'bank',
  'lender',
  'property_management',
  'construction',
  'contractor',
  'architecture',
  'accounting',
  'consulting',
  'insurance',
  'media',
  'government',
  'vendor',
  'partner',
  'internal_entity',
  'other',
]);

const RECORD_STATUS_KEYS = new Set(['active', 'inactive', 'prospect', 'archived']);

const RELATION_TYPE_KEYS = new Set([
  'parent',
  'subsidiary',
  'affiliate',
  'partner',
  'competitor',
  'vendor',
  'client',
  'investor',
  'other',
  'broker',
  'realtor',
]);

const PROJECT_LABELS: Record<string, string> = {
  '1812_h_pl': '1812 H Place',
  uniloft: 'Uniloft',
  '1313_penn': '1313 Penn',
  '1307_k_st': '1307 K',
  '2319_ontario': '2319 Ontario',
  reit: 'REIT',
  the_temple: 'The Temple',
};

function warningFlags(company: {
  notes?: string | null;
  primary_email?: string | null;
  primary_phone?: string | null;
  legal_name?: string | null;
  company_type?: string | null;
  addresses?: Array<{ country?: string | null; city?: string | null }>;
}): string[] {
  const notes = company.notes || '';
  const flags: string[] = [];
  const address = company.addresses?.[0];
  const incomplete =
    !company.primary_email && !company.primary_phone && !address?.country && !address?.city && !company.legal_name;
  if (/BILGI_EKSIK/i.test(notes) || incomplete) flags.push('BILGI_EKSIK');
  const ambiguous =
    /INCELEME_GEREKLI/i.test(notes) ||
    (!company.legal_name && (company.company_type === 'other' || /deterministic link/i.test(notes)));
  if (ambiguous) flags.push('INCELEME_GEREKLI');
  return flags;
}

function dash(value: string | null | undefined): string {
  return value?.trim() ? value : '—';
}

function commentsText(notes: string | null | undefined): string {
  if (!notes?.trim()) return '';
  return notes
    .replace(/BILGI_EKSIK/gi, '')
    .replace(/INCELEME_GEREKLI/gi, '')
    .replace(/deterministic link/gi, '')
    .replace(/[_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function displayOwner(name: string | null | undefined): string {
  return String(name || '')
    .replace(/\s*\((?:Demo|demo)\)\s*$/g, '')
    .trim();
}

export function CrmCompanyDetailView({ companyId }: { companyId: string }) {
  const t = useTranslations('crm.companies');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, user, canReadCompanies: canView, has } = useCrmAccess();
  const canUpdate = canUpdateCrm(user);
  const canTransferOwnership = has('transfer_ownership');
  const { openContact } = useContactCard();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const canQuery = !authLoading && canView;

  const detailQuery = useQuery({
    ...crmCompaniesQueries.detail(companyId),
    enabled: canQuery && Boolean(companyId),
  });
  const timelineQuery = useQuery({
    queryKey: crmCompaniesQueryKeys.timeline(companyId),
    queryFn: () => fetchCrmCompanyTimeline(companyId),
    enabled: canQuery,
  });
  const documentsQuery = useQuery({
    queryKey: ['crm', 'companies', 'documents', companyId],
    queryFn: async () => {
      const [crm, generic] = await Promise.all([
        fetchDocumentsByEntity('crm_company', companyId, { includeHidden: true, pageSize: 100 }).catch(() => ({
          items: [],
        })),
        fetchDocumentsByEntity('company', companyId, { includeHidden: true, pageSize: 100 }).catch(() => ({ items: [] })),
      ]);
      return [...(crm.items ?? []), ...(generic.items ?? [])];
    },
    enabled: canQuery,
  });
  const ownersQuery = useQuery({
    queryKey: ['crm', 'users', 'company-detail-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: editing && canTransferOwnership && canQuery,
  });

  const company = detailQuery.data;
  const [draft, setDraft] = useState<Record<string, string>>({});

  const startEdit = () => {
    if (!company) return;
    setDraft({
      display_name: company.display_name || '',
      primary_phone: company.primary_phone || '',
      primary_email: company.primary_email || '',
      website: company.website || '',
      industry: company.industry || '',
      source: company.source || '',
      notes: company.notes || '',
      owner_user_id: company.owner_user_id || '',
    });
    setEditing(true);
  };

  const saveMutation = useMutation({
    ...crmCompaniesMutations.update(companyId),
  });
  const transferMutation = useMutation({
    mutationFn: (ownerUserId: string) => transferCrmCompanyOwnership(companyId, ownerUserId),
  });
  const saving = saveMutation.isPending || transferMutation.isPending;

  const save = async () => {
    if (!company) return;
    const payload: Record<string, unknown> = {};
    if (canUpdate) {
      const pairs: Array<[string, string | null | undefined]> = [
        ['display_name', company.display_name],
        ['primary_phone', company.primary_phone],
        ['primary_email', company.primary_email],
        ['website', company.website],
        ['industry', company.industry],
        ['source', company.source],
        ['notes', company.notes],
      ];
      for (const [key, current] of pairs) {
        const next = draft[key] ?? '';
        if (next !== (current || '')) {
          payload[key] = next || null;
        }
      }
    }
    const nextOwner = draft.owner_user_id ?? '';
    const ownerChanged =
      canTransferOwnership && Boolean(nextOwner) && nextOwner !== (company.owner_user_id || '');
    if (Object.keys(payload).length === 0 && !ownerChanged) {
      setEditing(false);
      return;
    }
    try {
      if (Object.keys(payload).length > 0) await saveMutation.mutateAsync(payload);
      if (ownerChanged) await transferMutation.mutateAsync(nextOwner);
      setEditing(false);
      await queryClient.invalidateQueries({ queryKey: crmCompaniesQueryKeys.all });
    } catch {
      await queryClient.invalidateQueries({ queryKey: crmCompaniesQueryKeys.all });
    }
  };

  const brokers = useMemo(
    () => (company?.contacts ?? []).filter((contact) => /broker|realtor|acenta/i.test(`${contact.role} ${contact.job_title || ''} ${contact.relationship_type || ''}`)),
    [company],
  );
  const relatedBrokers = useMemo(
    () => (company?.related_people ?? []).filter((person) => person.is_broker),
    [company],
  );

  const companyTypeLabel = (type: string | null | undefined) =>
    type && COMPANY_TYPE_KEYS.has(type) ? t(`companyTypes.${type}` as 'companyTypes.other') : t('companyTypes.other');
  const statusLabel = (status: string | null | undefined) =>
    status && RECORD_STATUS_KEYS.has(status) ? t(`recordStatus.${status}` as 'recordStatus.active') : tCommon('noValue');
  const relationLabel = (type: string | null | undefined) =>
    type && RELATION_TYPE_KEYS.has(type) ? t(`relationTypes.${type}` as 'relationTypes.other') : '';
  const flagLabel = (flag: string) =>
    flag === 'BILGI_EKSIK' ? t('flags.missingInfo') : flag === 'INCELEME_GEREKLI' ? t('flags.reviewRequired') : flag;

  if (authLoading || detailQuery.isLoading) {
    return <LoadingState label={t('detail.loading')} />;
  }
  if (!canView) {
    return <ErrorState title={t('detail.accessDeniedTitle')} message={t('detail.accessDeniedMessage')} />;
  }
  if (detailQuery.isError || !company) {
    return (
      <ErrorState
        title={t('detail.loadFailedTitle')}
        message={t('detail.notFound')}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const flags = warningFlags(company);
  const address = (company.addresses ?? []).find((item) => item.is_primary) ?? company.addresses?.[0];
  const brokerPeople = relatedBrokers.length ? relatedBrokers : brokers.map((item) => ({
    id: item.contact_id,
    display_name: item.contact_display_name || item.contact_id,
  }));

  const comments = commentsText(company.notes);
  const addressLine = [address?.address_line1, address?.city, address?.country].filter(Boolean).join(', ');
  const lastActivity = company.last_activity_at || company.last_contact_at || timelineQuery.data?.items[0]?.created_at;

  return (
    <div className="crm-ops crm-ops--company-detail" data-testid="crm-g2-company-detail">
      <header className="crm-ops__header">
        <div>
          <h1>{company.display_name}</h1>
          <p>{companyTypeLabel(company.company_type)}</p>
          {flags.length ? (
            <div className="crm-ops-flags">
              {flags.map((flag) => (
                <span key={flag} className={`crm-ops-badge ${flag === 'BILGI_EKSIK' ? 'is-missing' : 'is-review'}`}>
                  {flagLabel(flag)}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="crm-ops__header-tools">
          {canUpdate || canTransferOwnership ? (
            editing ? (
              <>
                <Button type="button" size="sm" onClick={() => void save()} disabled={saving}>
                  {t('actions.save')}
                </Button>
                <Button type="button" size="sm" variant="secondary" onClick={() => setEditing(false)}>
                  {tCommon('cancel')}
                </Button>
              </>
            ) : (
              <Button type="button" size="sm" variant="secondary" onClick={startEdit} data-testid="crm-company-edit">
                {t('actions.edit')}
              </Button>
            )
          ) : null}
          <Link href={'/workspaces/crm/companies' as Route} className="ih-btn ih-btn--secondary">
            {t('actions.backToList')}
          </Link>
        </div>
      </header>

      <section className="crm-ops-section">
        <h2>{t('detail.companyInfo')}</h2>
        {editing ? (
          <div className="crm-ops-form">
            {canUpdate ? (
              <>
                <Input label={t('detail.companyName')} value={draft.display_name} onChange={(event) => setDraft((prev) => ({ ...prev, display_name: event.target.value }))} />
                <Input label={t('detail.phone')} value={draft.primary_phone} onChange={(event) => setDraft((prev) => ({ ...prev, primary_phone: event.target.value }))} />
                <Input label={t('detail.email')} value={draft.primary_email} onChange={(event) => setDraft((prev) => ({ ...prev, primary_email: event.target.value }))} />
                <Input label={t('detail.website')} value={draft.website} onChange={(event) => setDraft((prev) => ({ ...prev, website: event.target.value }))} />
                <Input label={t('detail.industry')} value={draft.industry} onChange={(event) => setDraft((prev) => ({ ...prev, industry: event.target.value }))} />
                <TextArea label={t('detail.comments')} value={draft.notes} onChange={(event) => setDraft((prev) => ({ ...prev, notes: event.target.value }))} />
              </>
            ) : null}
            {canTransferOwnership ? (
              <label className="ih-field">
                <span className="ih-field__label">{t('detail.owner')}</span>
                <select
                  className="ih-select"
                  data-testid="crm-company-owner"
                  value={draft.owner_user_id}
                  onChange={(event) => setDraft((prev) => ({ ...prev, owner_user_id: event.target.value }))}
                >
                  <option value="">—</option>
                  {(ownersQuery.data?.items ?? []).map((item) => (
                    <option key={item.id} value={item.id}>
                      {displayOwner(item.full_name) || item.full_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
        ) : (
          <dl className="crm-ops-kv">
            <dt>{t('detail.companyName')}</dt>
            <dd>{company.display_name}</dd>
            <dt>{t('detail.category')}</dt>
            <dd>{companyTypeLabel(company.company_type)}</dd>
            <dt>{t('detail.status')}</dt>
            <dd>{statusLabel(company.status)}</dd>
            <dt>{t('detail.phone')}</dt>
            <dd>{dash(company.primary_phone)}</dd>
            <dt>{t('detail.email')}</dt>
            <dd>{dash(company.primary_email)}</dd>
            <dt>{t('detail.website')}</dt>
            <dd>{dash(company.website)}</dd>
            <dt>{t('detail.address')}</dt>
            <dd>{dash(addressLine)}</dd>
            <dt>{t('detail.countryCity')}</dt>
            <dd>{dash([address?.country, address?.city].filter(Boolean).join(' / '))}</dd>
            <dt>{t('detail.owner')}</dt>
            <dd>{dash(displayOwner(company.owner_name))}</dd>
            <dt>{t('detail.lastActivity')}</dt>
            <dd>{lastActivity ? new Date(lastActivity).toLocaleString(locale) : tCommon('noValue')}</dd>
          </dl>
        )}
      </section>

      <section className="crm-ops-section">
        <h2>{t('detail.relatedPeople')}</h2>
        {company.contacts.length === 0 ? (
          <p className="crm-ops-muted">—</p>
        ) : (
          <ul className="crm-ops-list">
            {company.contacts.map((contact) => (
              <li key={contact.id}>
                <button type="button" className="crm-ops-link" onClick={() => openContact(contact.contact_id)}>
                  {contact.contact_display_name ?? contact.contact_id}
                </button>
                <span>{contact.job_title || relationLabel(contact.role)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {brokerPeople.length ? (
        <section className="crm-ops-section">
          <h2>{t('detail.brokers')}</h2>
          <ul className="crm-ops-list">
            {brokerPeople.map((person) => (
              <li key={person.id}>
                <button type="button" className="crm-ops-link" onClick={() => openContact(person.id)}>
                  {person.display_name}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="crm-ops-section">
        <h2>{t('detail.openWork')}</h2>
        {(company.related_agreements ?? []).length === 0 ? (
          <p className="crm-ops-muted">—</p>
        ) : (
          <ul className="crm-ops-list">
            {(company.related_agreements ?? []).map((agreement) => (
              <li key={agreement.id}>
                <Link href={`/workspaces/crm/contacts/${agreement.contact_id}/satin-alma/${agreement.id}` as Route} className="crm-ops-link">
                  {PROJECT_LABELS[agreement.project_group] || agreement.project_group}
                  {agreement.unit_number ? ` · ${agreement.unit_number}` : ''}
                </Link>
                <span>
                  {agreement.contact_display_name}
                  {agreement.investment_amount ? ` · ${agreement.investment_amount}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="crm-ops-section">
        <h2>{t('detail.relationshipTypes')}</h2>
        {company.relationships.length === 0 ? (
          <p className="crm-ops-muted">—</p>
        ) : (
          <ul className="crm-ops-list">
            {company.relationships.map((rel) => (
              <li key={rel.id}>
                <Link href={`/workspaces/crm/companies/${rel.target_company_id}` as Route} className="crm-ops-link">
                  {rel.target_display_name ?? rel.target_company_id}
                </Link>
                <span>{relationLabel(rel.relationship_type) || tCommon('noValue')}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="crm-ops-section">
        <h2>{t('detail.comments')}</h2>
        {comments ? <p className="crm-ops-note">{comments}</p> : <p className="crm-ops-muted">—</p>}
      </section>

      <section className="crm-ops-section">
        <h2>{t('detail.documents')}</h2>
        <DocumentGallery
          documents={documentsQuery.data ?? []}
          entityType="crm_company"
          entityId={companyId}
          onChanged={() => void documentsQuery.refetch()}
        />
      </section>
    </div>
  );
}
