'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';
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
import { fetchCrmCompanyTimeline } from '@/workspaces/crm/api/companies';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { DocumentGallery } from '@/workspaces/crm/contact-card/document-gallery';

import '@/workspaces/crm/contact-card/contact-card.css';
import '../companies/companies-ops.css';

const TYPE_LABELS: Record<string, string> = {
  investment_company: 'Yatırımcı',
  buyer_entity: 'Alıcı şirketi',
  brokerage: 'Broker / Acenta',
  law_firm: 'Hukuk',
  bank: 'Banka',
  lender: 'Finansör',
  property_management: 'Yönetim',
  construction: 'İnşaat',
  contractor: 'Yüklenici',
  architecture: 'Mimarlık',
  accounting: 'Muhasebe',
  consulting: 'Danışmanlık',
  insurance: 'Sigorta',
  media: 'Medya',
  government: 'Kamu',
  vendor: 'Tedarikçi',
  partner: 'Partner',
  internal_entity: 'İç şirket',
  other: 'Diğer',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Aktif',
  inactive: 'Pasif',
  prospect: 'Aday',
  archived: 'Arşiv',
};

const RELATION_TYPE_LABELS: Record<string, string> = {
  parent: 'Ana şirket',
  subsidiary: 'Bağlı şirket',
  affiliate: 'İştirak',
  partner: 'Partner',
  competitor: 'Rakip',
  vendor: 'Tedarikçi',
  client: 'Müşteri',
  investor: 'Yatırımcı',
  other: 'Diğer',
  broker: 'Broker',
  realtor: 'Acenta',
};

const FLAG_LABELS: Record<string, string> = {
  BILGI_EKSIK: 'Bilgi Eksik',
  INCELEME_GEREKLI: 'İnceleme Gerekli',
};

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
  const { authLoading, user, canReadCompanies: canView } = useCrmAccess();
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
    enabled: editing && canQuery,
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
    onSuccess: async () => {
      setEditing(false);
      await queryClient.invalidateQueries({ queryKey: crmCompaniesQueryKeys.all });
    },
  });

  const save = () => {
    if (!company) return;
    const payload: Record<string, unknown> = {};
    const pairs: Array<[string, string | null | undefined]> = [
      ['display_name', company.display_name],
      ['primary_phone', company.primary_phone],
      ['primary_email', company.primary_email],
      ['website', company.website],
      ['industry', company.industry],
      ['source', company.source],
      ['notes', company.notes],
      ['owner_user_id', company.owner_user_id],
    ];
    for (const [key, current] of pairs) {
      const next = draft[key] ?? '';
      if (next !== (current || '')) {
        payload[key] = next || null;
      }
    }
    if (Object.keys(payload).length === 0) {
      setEditing(false);
      return;
    }
    saveMutation.mutate(payload);
  };

  const brokers = useMemo(
    () => (company?.contacts ?? []).filter((contact) => /broker|realtor|acenta/i.test(`${contact.role} ${contact.job_title || ''} ${contact.relationship_type || ''}`)),
    [company],
  );
  const relatedBrokers = useMemo(
    () => (company?.related_people ?? []).filter((person) => person.is_broker),
    [company],
  );

  if (authLoading || detailQuery.isLoading) {
    return <LoadingState label="Şirket yükleniyor…" />;
  }
  if (!canView) {
    return <ErrorState title="Erişim yok" message="Şirketleri görüntüleme izniniz yok." />;
  }
  if (detailQuery.isError || !company) {
    return (
      <ErrorState
        title="Yüklenemedi"
        message={detailQuery.error?.message ?? 'Şirket bulunamadı'}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            Yeniden dene
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
          <p>{TYPE_LABELS[company.company_type] || 'Diğer'}</p>
          {flags.length ? (
            <div className="crm-ops-flags">
              {flags.map((flag) => (
                <span key={flag} className={`crm-ops-badge ${flag === 'BILGI_EKSIK' ? 'is-missing' : 'is-review'}`}>
                  {FLAG_LABELS[flag] || flag}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="crm-ops__header-tools">
          {canUpdateCrm(user) ? (
            editing ? (
              <>
                <Button type="button" size="sm" onClick={save} disabled={saveMutation.isPending}>
                  Kaydet
                </Button>
                <Button type="button" size="sm" variant="secondary" onClick={() => setEditing(false)}>
                  Vazgeç
                </Button>
              </>
            ) : (
              <Button type="button" size="sm" variant="secondary" onClick={startEdit} data-testid="crm-company-edit">
                Düzenle
              </Button>
            )
          ) : null}
          <Link href={'/workspaces/crm/companies' as Route} className="ih-btn ih-btn--secondary">
            Listeye dön
          </Link>
        </div>
      </header>

      <section className="crm-ops-section">
        <h2>Şirket bilgileri</h2>
        {editing ? (
          <div className="crm-ops-form">
            <Input label="Şirket adı" value={draft.display_name} onChange={(event) => setDraft((prev) => ({ ...prev, display_name: event.target.value }))} />
            <Input label="Telefon" value={draft.primary_phone} onChange={(event) => setDraft((prev) => ({ ...prev, primary_phone: event.target.value }))} />
            <Input label="E-posta" value={draft.primary_email} onChange={(event) => setDraft((prev) => ({ ...prev, primary_email: event.target.value }))} />
            <Input label="Web sitesi" value={draft.website} onChange={(event) => setDraft((prev) => ({ ...prev, website: event.target.value }))} />
            <Input label="Sektör" value={draft.industry} onChange={(event) => setDraft((prev) => ({ ...prev, industry: event.target.value }))} />
            <label className="ih-field">
              <span className="ih-field__label">Sorumlu</span>
              <select
                className="ih-select"
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
            <TextArea label="Yorumlar" value={draft.notes} onChange={(event) => setDraft((prev) => ({ ...prev, notes: event.target.value }))} />
          </div>
        ) : (
          <dl className="crm-ops-kv">
            <dt>Şirket adı</dt>
            <dd>{company.display_name}</dd>
            <dt>Kategori</dt>
            <dd>{TYPE_LABELS[company.company_type] || 'Diğer'}</dd>
            <dt>Durum</dt>
            <dd>{STATUS_LABELS[company.status] || '—'}</dd>
            <dt>Telefon</dt>
            <dd>{dash(company.primary_phone)}</dd>
            <dt>E-posta</dt>
            <dd>{dash(company.primary_email)}</dd>
            <dt>Web sitesi</dt>
            <dd>{dash(company.website)}</dd>
            <dt>Adres</dt>
            <dd>{dash(addressLine)}</dd>
            <dt>Ülke / Şehir</dt>
            <dd>{dash([address?.country, address?.city].filter(Boolean).join(' / '))}</dd>
            <dt>Sorumlu</dt>
            <dd>{dash(displayOwner(company.owner_name))}</dd>
            <dt>Son etkinlik</dt>
            <dd>{lastActivity ? new Date(lastActivity).toLocaleString('tr-TR') : '—'}</dd>
          </dl>
        )}
      </section>

      <section className="crm-ops-section">
        <h2>İlgili kişiler</h2>
        {company.contacts.length === 0 ? (
          <p className="crm-ops-muted">—</p>
        ) : (
          <ul className="crm-ops-list">
            {company.contacts.map((contact) => (
              <li key={contact.id}>
                <button type="button" className="crm-ops-link" onClick={() => openContact(contact.contact_id)}>
                  {contact.contact_display_name ?? contact.contact_id}
                </button>
                <span>{contact.job_title || RELATION_TYPE_LABELS[contact.role] || ''}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {brokerPeople.length ? (
        <section className="crm-ops-section">
          <h2>Broker / Acenta kişileri</h2>
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
        <h2>Açık proje / işler</h2>
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
        <h2>İlişki türleri</h2>
        {company.relationships.length === 0 ? (
          <p className="crm-ops-muted">—</p>
        ) : (
          <ul className="crm-ops-list">
            {company.relationships.map((rel) => (
              <li key={rel.id}>
                <Link href={`/workspaces/crm/companies/${rel.target_company_id}` as Route} className="crm-ops-link">
                  {rel.target_display_name ?? rel.target_company_id}
                </Link>
                <span>{RELATION_TYPE_LABELS[rel.relationship_type] || '—'}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="crm-ops-section">
        <h2>Yorumlar</h2>
        {comments ? <p className="crm-ops-note">{comments}</p> : <p className="crm-ops-muted">—</p>}
      </section>

      <section className="crm-ops-section">
        <h2>Belgeler</h2>
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
