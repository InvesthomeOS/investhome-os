'use client';

import { useEffect, useState } from 'react';

import { Input, Select, TextArea } from '@investhome/ui';

import { fetchContacts } from '@/workspaces/crm/api/contacts';
import { crmSourceChoices } from '@/workspaces/crm/crm-source-options';

export type CrmPersonDraft = {
  contact_id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  address: string;
  city: string;
  region: string;
  country: string;
  language: string;
  company: string;
  position: string;
  source: string;
  owner_user_id: string;
  next_follow_up: string;
  notes: string;
  status: string;
};

export const EMPTY_PERSON_DRAFT: CrmPersonDraft = {
  contact_id: '',
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  region: '',
  country: '',
  language: '',
  company: '',
  position: '',
  source: 'manual',
  owner_user_id: '',
  next_follow_up: '',
  notes: '',
  status: 'active',
};

export type CrmUserOption = { id: string; name: string };

export function CrmContactPicker({
  selectedId,
  selectedName,
  onSelect,
  projectId,
  projectGroup,
}: {
  selectedId: string;
  selectedName: string;
  onSelect: (contact: { id: string; name: string; phone?: string | null; email?: string | null } | null) => void;
  projectId?: string;
  projectGroup?: string;
}) {
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState<Array<{ id: string; display_name: string; primary_phone?: string | null; primary_email?: string | null }>>([]);
  const scoped = Boolean(projectId || projectGroup);

  useEffect(() => {
    const needle = query.trim();
    if (!scoped && needle.length < 2) {
      setMatches([]);
      return;
    }
    const handle = window.setTimeout(() => {
      void (async () => {
        const collected: Array<{ id: string; display_name: string; primary_phone?: string | null; primary_email?: string | null }> = [];
        let page = 1;
        let total = 0;
        do {
          const result = await fetchContacts({
            search: needle.length >= 2 ? needle : undefined,
            project_id: projectId,
            agreement_project: projectGroup,
            page,
            page_size: scoped ? 100 : 8,
          });
          collected.push(...result.items);
          total = result.total ?? collected.length;
          page += 1;
        } while (scoped && collected.length < total && page <= 10);
        setMatches(collected);
      })().catch(() => setMatches([]));
    }, scoped && needle.length < 2 ? 0 : 250);
    return () => window.clearTimeout(handle);
  }, [projectGroup, projectId, query, scoped]);

  return (
    <div className="crm-person-picker">
      <Input label="Mevcut kişi ara" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ad, telefon veya e-posta" />
      {selectedId ? (
        <p>
          Seçilen kişi: <strong>{selectedName || selectedId}</strong>{' '}
          <button type="button" onClick={() => onSelect(null)}>Temizle</button>
        </p>
      ) : null}
      {matches.length ? (
        <ul>
          {matches.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect({
                    id: item.id,
                    name: item.display_name,
                    phone: item.primary_phone,
                    email: item.primary_email,
                  });
                  setQuery('');
                  setMatches([]);
                }}
              >
                {item.display_name}
                {item.primary_phone ? ` · ${item.primary_phone}` : ''}
                {item.primary_email ? ` · ${item.primary_email}` : ''}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function CrmPersonFields({
  value,
  onChange,
  users = [],
  showStatus = false,
  showNotes = true,
  locked = false,
}: {
  value: CrmPersonDraft;
  onChange: (next: CrmPersonDraft) => void;
  users?: CrmUserOption[];
  showStatus?: boolean;
  showNotes?: boolean;
  locked?: boolean;
}) {
  const set = (patch: Partial<CrmPersonDraft>) => onChange({ ...value, ...patch });
  const sources = crmSourceChoices(value.source);
  const sourceValue = sources.some((item) => item.value === value.source) ? value.source : value.source;
  return (
    <div className="crm-person-fields">
      <Input label="Ad" value={value.first_name} disabled={locked} onChange={(event) => set({ first_name: event.target.value })} />
      <Input label="Soyad" value={value.last_name} disabled={locked} onChange={(event) => set({ last_name: event.target.value })} />
      <Input label="Telefon" value={value.phone} disabled={locked} onChange={(event) => set({ phone: event.target.value })} />
      <Input label="E-posta" value={value.email} disabled={locked} onChange={(event) => set({ email: event.target.value })} />
      <Input label="Adres" value={value.address} disabled={locked} onChange={(event) => set({ address: event.target.value })} />
      <Input label="Şehir" value={value.city} disabled={locked} onChange={(event) => set({ city: event.target.value })} />
      <Input label="Bölge / Eyalet" value={value.region} disabled={locked} onChange={(event) => set({ region: event.target.value })} />
      <Input label="Ülke" value={value.country} disabled={locked} onChange={(event) => set({ country: event.target.value })} />
      <Select label="Dil" value={value.language} disabled={locked} onChange={(event) => set({ language: event.target.value })}>
        <option value="">Seçin</option>
        <option value="tr">Türkçe</option>
        <option value="en">English</option>
        <option value="de">Deutsch</option>
        <option value="ru">Русский</option>
        <option value="ar">العربية</option>
      </Select>
      <Input label="Şirket" value={value.company} disabled={locked} onChange={(event) => set({ company: event.target.value })} />
      <Input label="Pozisyon" value={value.position} disabled={locked} onChange={(event) => set({ position: event.target.value })} />
      <Select label="Geliş Kaynağı" value={sourceValue} disabled={locked} onChange={(event) => set({ source: event.target.value })}>
        {sources.map((item) => (
          <option key={item.value} value={item.value}>{item.label}</option>
        ))}
      </Select>
      <Select label="Sorumlu" value={value.owner_user_id} disabled={locked} onChange={(event) => set({ owner_user_id: event.target.value })}>
        <option value="">Seçin</option>
        {users.map((item) => (
          <option key={item.id} value={item.id}>{item.name}</option>
        ))}
      </Select>
      <Input label="Sonraki Takip" type="datetime-local" value={value.next_follow_up} disabled={locked} onChange={(event) => set({ next_follow_up: event.target.value })} />
      {showStatus ? (
        <Select label="Durum" value={value.status} disabled={locked} onChange={(event) => set({ status: event.target.value })}>
          <option value="active">Aktif</option>
          <option value="archived">Junk</option>
        </Select>
      ) : null}
      {showNotes ? (
        <TextArea label="Notlar" value={value.notes} disabled={locked} rows={3} onChange={(event) => set({ notes: event.target.value })} />
      ) : null}
    </div>
  );
}

export function personPayload(draft: CrmPersonDraft) {
  return {
    contact_id: draft.contact_id || null,
    first_name: draft.first_name.trim() || null,
    last_name: draft.last_name.trim() || null,
    phone: draft.phone.trim() || null,
    email: draft.email.trim() || null,
    source: draft.source || null,
    address_line1: draft.address.trim() || null,
    city: draft.city.trim() || null,
    state_province: draft.region.trim() || null,
    country: draft.country.trim() || null,
    language: draft.language.trim() || null,
    organization_name: draft.company.trim() || null,
    job_title: draft.position.trim() || null,
    notes: draft.notes.trim() || null,
    owner_user_id: draft.owner_user_id || null,
    next_follow_up_at: draft.next_follow_up ? new Date(draft.next_follow_up).toISOString() : null,
  };
}
