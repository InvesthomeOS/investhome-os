'use client';

import { useEffect, useState } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, KpiCard, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  exportBitrixVerificationCsv,
  fetchBitrixVerificationSummary,
  fetchJunkReasons,
  type ContactListParams,
} from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmContactStatus } from '@/workspaces/crm/types';

import './ds/contacts-ds.css';

const PAGE_SIZE = 25;

const AGREEMENT_PROJECTS = [
  { value: '1307_k_st', label: '1307 K St' },
  { value: '1313_penn', label: '1313 Penn' },
  { value: '1812_h_pl', label: '1812 H Pl' },
  { value: '2319_ontario', label: '2319 Ontario' },
  { value: 'reit', label: 'REIT' },
  { value: 'the_temple', label: 'The Temple' },
  { value: 'uniloft', label: 'Uniloft' },
] as const;

const COPY = {
  tr: {
    title: 'Kişiler',
    subtitle: 'Gerçek CRM kişi kayıtları — Bitrix aktarım doğrulaması',
    search: 'Ad, telefon veya e-posta ara',
    source: 'Kaynak',
    status: 'Durum',
    category: 'Kategori / Tür',
    junkReason: 'Junk Sebebi',
    agreementProject: 'Anlaşma Projesi',
    all: 'Tümü',
    bitrix: 'Bitrix',
    otherSource: 'Diğer / mevcut OS',
    active: 'Aktif',
    archived: 'Junk',
    customer: 'Müşteri',
    agent: 'Acenta',
    agreement: 'Anlaşmalı',
    allReasons: 'Tüm sebepler',
    allProjects: 'Tüm projeler',
    export: 'Bitrix doğrulama CSV',
    name: 'Ad Soyad',
    phone: 'Telefon',
    email: 'E-posta',
    owner: 'Sorumlu',
    lastActivity: 'Son aktivite',
    updated: 'Son Güncelleme',
    empty: 'Bu filtrelerle eşleşen kişi yok.',
    previous: 'Önceki',
    next: 'Sonraki',
    total: 'Toplam CRM Kişisi',
    bitrixContacts: 'Bitrix Kişileri',
    activeBitrix: 'Aktif Bitrix',
    archivedBitrix: 'Junk / Arşiv Bitrix',
  },
  en: {
    title: 'Contacts',
    subtitle: 'Live CRM contacts — Bitrix transfer verification',
    search: 'Search name, phone or email',
    source: 'Source',
    status: 'Status',
    category: 'Category / Type',
    junkReason: 'Junk reason',
    agreementProject: 'Agreement project',
    all: 'All',
    bitrix: 'Bitrix',
    otherSource: 'Other / existing OS',
    active: 'Active',
    archived: 'Junk',
    customer: 'Customer',
    agent: 'Agent',
    agreement: 'Agreement',
    allReasons: 'All reasons',
    allProjects: 'All projects',
    export: 'Bitrix verification CSV',
    name: 'Name',
    phone: 'Phone',
    email: 'Email',
    owner: 'Owner',
    lastActivity: 'Last activity',
    updated: 'Last Updated',
    empty: 'No contacts match these filters.',
    previous: 'Previous',
    next: 'Next',
    total: 'Total CRM Contacts',
    bitrixContacts: 'Bitrix Contacts',
    activeBitrix: 'Active Bitrix',
    archivedBitrix: 'Junk / Archived Bitrix',
  },
} as const;

type CategoryFilter = '' | 'customer' | 'agent' | 'agreement';

function categoryLabel(
  copy: (typeof COPY)['tr'],
  contact: { is_agent?: boolean; has_agreements?: boolean },
): string {
  const parts: string[] = [];
  if (contact.is_agent) parts.push(copy.agent);
  if (contact.has_agreements) parts.push(copy.agreement);
  if (!parts.length) parts.push(copy.customer);
  return parts.join(' · ');
}

export function ContactsLiveVerificationWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const { openContact } = useContactCard();
  const { authLoading, canRead, has } = useCrmAccess();
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [source, setSource] = useState<'' | 'bitrix' | 'other'>('');
  const [status, setStatus] = useState<'' | CrmContactStatus>('');
  const [category, setCategory] = useState<CategoryFilter>('');
  const [junkReason, setJunkReason] = useState('');
  const [agreementProject, setAgreementProject] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const params: ContactListParams = {
    search: search || undefined,
    source_group: source || undefined,
    status: status || undefined,
    category: category || undefined,
    junk_reason: junkReason || undefined,
    agreement_project: agreementProject || undefined,
    include_archived: status !== 'active',
    sort_by: 'updated_at',
    sort_dir: 'desc',
    page,
    page_size: PAGE_SIZE,
  };
  const contactsQuery = useQuery({
    ...contactQueries.list(params),
    enabled: !authLoading && canRead,
  });
  const summaryQuery = useQuery({
    queryKey: ['crm', 'contacts', 'bitrix-verification-summary'],
    queryFn: fetchBitrixVerificationSummary,
    enabled: !authLoading && canRead,
  });
  const reasonsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'junk-reasons'],
    queryFn: fetchJunkReasons,
    enabled: !authLoading && canRead,
  });
  const rows = contactsQuery.data?.items ?? [];
  const pages = Math.max(1, contactsQuery.data?.pages ?? 1);
  const summary = summaryQuery.data;

  const downloadExport = async () => {
    const blob = await exportBitrixVerificationCsv();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'bitrix-contact-verification.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="ctc-ds" data-testid="contacts-ds-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        {has('export') ? (
          <Button variant="secondary" size="sm" onClick={() => void downloadExport()}>
            <IhIcon name="documents" size={13} />
            {copy.export}
          </Button>
        ) : null}
      </header>

      <section className="ctc-ds__kpi-row" aria-label="Bitrix verification summary">
        {[
          [copy.total, summary?.total_contacts],
          [copy.bitrixContacts, summary?.bitrix_contacts],
          [copy.activeBitrix, summary?.active_bitrix],
          [copy.archivedBitrix, summary?.archived_bitrix],
        ].map(([label, value]) => (
          <KpiCard key={String(label)} className="ctc-ds__kpi" label={String(label)} value={value == null ? '—' : Number(value).toLocaleString(locale)} />
        ))}
      </section>

      <section className="ctc-ds__toolbar" aria-label="Contact verification filters">
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.search}
          data-testid="contacts-ds-search"
        />
        <Select label={copy.status} value={status} onChange={(event) => { setStatus(event.target.value as typeof status); setPage(1); }} data-testid="contacts-status-filter">
          <option value="">{copy.all}</option>
          <option value="active">{copy.active}</option>
          <option value="archived">{copy.archived}</option>
        </Select>
        <Select label={copy.category} value={category} onChange={(event) => { setCategory(event.target.value as CategoryFilter); setPage(1); }} data-testid="contacts-category-filter">
          <option value="">{copy.all}</option>
          <option value="customer">{copy.customer}</option>
          <option value="agent">{copy.agent}</option>
          <option value="agreement">{copy.agreement}</option>
        </Select>
        <Select label={copy.junkReason} value={junkReason} onChange={(event) => { setJunkReason(event.target.value); setPage(1); }} data-testid="contacts-junk-reason-filter">
          <option value="">{copy.allReasons}</option>
          {(reasonsQuery.data?.items ?? []).map((item) => (
            <option key={item.reason} value={item.reason}>
              {item.reason} ({item.count})
            </option>
          ))}
        </Select>
        <Select label={copy.source} value={source} onChange={(event) => { setSource(event.target.value as typeof source); setPage(1); }}>
          <option value="">{copy.all}</option>
          <option value="bitrix">{copy.bitrix}</option>
          <option value="other">{copy.otherSource}</option>
        </Select>
        <Select label={copy.agreementProject} value={agreementProject} onChange={(event) => { setAgreementProject(event.target.value); setPage(1); }}>
          <option value="">{copy.allProjects}</option>
          {AGREEMENT_PROJECTS.map((project) => (
            <option key={project.value} value={project.value}>{project.label}</option>
          ))}
        </Select>
      </section>

      <section className="ctc-ds__table-section" aria-label="Real CRM contacts">
        {contactsQuery.isLoading ? <div className="ctc-ds__skeleton">Loading…</div> : null}
        {contactsQuery.isError ? <div className="ctc-ds__empty">{contactsQuery.error.message}</div> : null}
        {!contactsQuery.isLoading && !contactsQuery.isError && rows.length === 0 ? (
          <div className="ctc-ds__empty">{copy.empty}</div>
        ) : null}
        {rows.length ? (
          <div className="ctc-ds__table-wrap">
            <table className="ctc-ds__table">
              <thead>
                <tr>
                  <th>{copy.name}</th><th>{copy.phone}</th><th>{copy.email}</th>
                  <th>{copy.status}</th><th>{copy.category}</th><th>{copy.owner}</th>
                  <th>{copy.lastActivity}</th><th>{copy.junkReason}</th>
                  <th>{copy.source}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((contact) => (
                  <tr
                    key={contact.id}
                    className="ctc-ds__row"
                    data-testid={`contacts-ds-row-${contact.id}`}
                    onClick={() => openContact(contact.id)}
                  >
                    <td><strong>{contact.display_name}</strong></td>
                    <td>{contact.primary_phone ?? '—'}</td>
                    <td>{contact.primary_email ?? '—'}</td>
                    <td><StatusChip tone={contact.status === 'active' ? 'success' : 'default'}>{contact.status === 'active' ? copy.active : copy.archived}</StatusChip></td>
                    <td>{categoryLabel(copy, contact)}</td>
                    <td>{contact.owner_name ?? contact.bitrix_responsible ?? '—'}</td>
                    <td>{contact.last_contact_at ? new Date(contact.last_contact_at).toLocaleString(locale) : '—'}</td>
                    <td>{contact.junk_reason ?? '—'}</td>
                    <td>{contact.source ?? copy.otherSource}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {contactsQuery.data?.total ? (
        <div className="ctc-ds__pagination">
          <span>{page} / {pages} · {contactsQuery.data.total.toLocaleString(locale)}</span>
          <div>
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>{copy.previous}</Button>
            <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>{copy.next}</Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
