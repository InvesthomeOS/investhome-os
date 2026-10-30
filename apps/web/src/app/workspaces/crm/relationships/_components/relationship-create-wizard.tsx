'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select } from '@investhome/ui';

import { fetchProjects } from '@/lib/api/projects';
import { confirmDiscardUnsaved } from '@/lib/crm/unsaved-form';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchCrmCompanies } from '@/workspaces/crm/api/companies';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import { relationshipMutations } from '@/workspaces/crm/hooks/use-relationships';
import type { RelationshipEntityType } from '@/workspaces/crm/api/relationships';

import '../../contacts/_components/people-workspace.css';
import '../../contacts/_components/ds/contacts-ds.css';
import './relationships-workspace.css';

type PairOption = {
  value: string;
  category: string;
  label: string;
};

const COPY = {
  tr: {
    title: 'Yeni İlişki',
    back: 'İlişkilere dön',
    subtitle: 'Yalnızca mevcut CRM kayıtları arasında ilişki oluşturur. Yeni kişi veya şirket açmaz.',
    source: 'Kaynak',
    target: 'Hedef',
    entityType: 'Kayıt türü',
    search: 'Mevcut kaydı ara',
    type: 'İlişki türü',
    category: 'Kategori',
    notes: 'Not',
    submit: 'İlişkiyi kaydet',
    duplicate: 'Bu ilişki zaten kayıtlı.',
    createFailed: 'İlişki oluşturulamadı',
    accessDenied: 'Erişim yok',
    contact: 'Kişi',
    company: 'Şirket',
    project: 'Proje',
    selected: 'Seçildi',
    cancel: 'Vazgeç',
    searchHint: 'En az 2 karakter yazın',
    empty: 'Kayıt bulunamadı',
    loadFailed: 'Kayıtlar yüklenemedi. Yeniden deneyin.',
    retry: 'Yeniden dene',
    loading: 'Yükleniyor…',
    openExisting: 'Mevcut ilişkiyi aç',
  },
  en: {
    title: 'New relationship',
    back: 'Back to relationships',
    subtitle: 'Links existing CRM records only. Does not create people or companies.',
    source: 'Source',
    target: 'Target',
    entityType: 'Record type',
    search: 'Search existing record',
    type: 'Relationship type',
    category: 'Category',
    notes: 'Note',
    submit: 'Save relationship',
    duplicate: 'This relationship already exists.',
    createFailed: 'Could not create relationship',
    accessDenied: 'Access denied',
    contact: 'Person',
    company: 'Company',
    project: 'Project',
    selected: 'Selected',
    cancel: 'Cancel',
    searchHint: 'Type at least 2 characters',
    empty: 'No records found',
    loadFailed: 'Records could not be loaded. Try again.',
    retry: 'Retry',
    loading: 'Loading…',
    openExisting: 'Open existing relationship',
  },
} as const;

const CATEGORY_LABELS: Record<string, string> = {
  organizational: 'Organizasyonel',
  commercial: 'Ticari',
  personal: 'Kişisel',
  investment: 'Yatırım',
};

function typesForPair(sourceType: RelationshipEntityType, targetType: RelationshipEntityType): PairOption[] {
  const pair = [sourceType, targetType].sort().join('|');
  if (pair === 'company|contact') {
    return [{ value: 'contact_company', category: 'organizational', label: 'Kişi ↔ Şirket' }];
  }
  if (sourceType === 'contact' && targetType === 'contact') {
    return [
      { value: 'colleague', category: 'personal', label: 'Kişi ↔ Kişi' },
      { value: 'partner', category: 'commercial', label: 'Ortaklık / Co-owner' },
    ];
  }
  if (pair === 'contact|project') {
    return [{ value: 'investor', category: 'investment', label: 'Kişi ↔ Proje / Yatırım' }];
  }
  if (pair === 'company|project') {
    return [{ value: 'company_project', category: 'commercial', label: 'Şirket ↔ Proje' }];
  }
  if (sourceType === 'company' && targetType === 'company') {
    return [{ value: 'partner', category: 'commercial', label: 'Ortaklık / Co-owner' }];
  }
  return [];
}

function EntityPicker({
  label,
  entityType,
  entityId,
  search,
  onType,
  onSearch,
  onSelect,
  copy,
}: {
  label: string;
  entityType: RelationshipEntityType;
  entityId: string;
  search: string;
  onType: (value: RelationshipEntityType) => void;
  onSearch: (value: string) => void;
  onSelect: (id: string, name: string) => void;
  copy: (typeof COPY)[keyof typeof COPY];
}) {
  const contactsQuery = useQuery({
    ...contactQueries.list({ search: search || undefined, page: 1, page_size: 20 }),
    enabled: entityType === 'contact' && search.trim().length >= 2,
  });
  const companiesQuery = useQuery({
    queryKey: ['crm', 'companies', 'relationship-picker', search],
    queryFn: () => fetchCrmCompanies({ search, page: 1, pageSize: 20 }),
    enabled: entityType === 'company' && search.trim().length >= 2,
  });
  const projectsQuery = useQuery({
    queryKey: ['projects', 'relationship-picker', search],
    queryFn: () => fetchProjects({ search, page: 1, page_size: 20 }),
    enabled: entityType === 'project' && search.trim().length >= 2,
  });

  const activeQuery = entityType === 'contact' ? contactsQuery : entityType === 'company' ? companiesQuery : projectsQuery;
  const searching = search.trim().length >= 2;
  const options =
    entityType === 'contact'
      ? (contactsQuery.data?.items ?? []).map((item) => ({ id: item.id, name: item.display_name }))
      : entityType === 'company'
        ? (companiesQuery.data?.items ?? []).map((item) => ({ id: item.id, name: item.display_name }))
        : (projectsQuery.data?.items ?? []).map((item) => ({ id: item.id, name: item.project_name }));

  return (
    <div>
      <h2>{label}</h2>
      <Select label={copy.entityType} value={entityType} onChange={(event) => onType(event.target.value as RelationshipEntityType)}>
        <option value="contact">{copy.contact}</option>
        <option value="company">{copy.company}</option>
        <option value="project">{copy.project}</option>
      </Select>
      <Input label={copy.search} value={search} onChange={(event) => onSearch(event.target.value)} placeholder={copy.search} />
      <div className="crm-rel-entity-results" data-testid="crm-rel-picker">
        {!searching ? <p data-testid="crm-rel-picker-hint">{copy.searchHint}</p> : null}
        {searching && (activeQuery.isLoading || activeQuery.isFetching) && !activeQuery.data ? (
          <p data-testid="crm-rel-picker-loading">{copy.loading}</p>
        ) : null}
        {searching && activeQuery.isError ? (
          <div data-testid="crm-rel-picker-error">
            <p>{copy.loadFailed}</p>
            <Button type="button" size="sm" onClick={() => void activeQuery.refetch()}>
              {copy.retry}
            </Button>
          </div>
        ) : null}
        {searching && !activeQuery.isLoading && !activeQuery.isFetching && !activeQuery.isError && options.length === 0 ? (
          <p data-testid="crm-rel-picker-empty">{copy.empty}</p>
        ) : null}
        {options.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.id === entityId ? 'is-selected' : undefined}
            onClick={() => onSelect(item.id, item.name)}
          >
            <span>{item.name}</span>
            {item.id === entityId ? <strong>{copy.selected}</strong> : null}
          </button>
        ))}
      </div>
    </div>
  );
}

export function RelationshipCreateWizard() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const router = useRouter();
  const { authLoading, canCreate } = useCrmAccess();
  const [sourceType, setSourceType] = useState<RelationshipEntityType>('contact');
  const [targetType, setTargetType] = useState<RelationshipEntityType>('company');
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [sourceName, setSourceName] = useState('');
  const [targetName, setTargetName] = useState('');
  const [sourceSearch, setSourceSearch] = useState('');
  const [targetSearch, setTargetSearch] = useState('');
  const [relationshipType, setRelationshipType] = useState('contact_company');
  const [notes, setNotes] = useState('');
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);
  const [duplicateId, setDuplicateId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const typeOptions = useMemo(() => typesForPair(sourceType, targetType), [sourceType, targetType]);
  const selectedType = typeOptions.find((item) => item.value === relationshipType) ?? typeOptions[0];

  useEffect(() => {
    if (selectedType && selectedType.value !== relationshipType) {
      setRelationshipType(selectedType.value);
    }
  }, [relationshipType, selectedType]);

  const createMutation = useMutation({
    mutationFn: relationshipMutations.create,
    onSuccess: () => router.push('/workspaces/crm/relationships'),
    onError: () => setSaveError(copy.createFailed),
  });

  const dirty = Boolean(sourceId || targetId || sourceSearch.trim() || targetSearch.trim() || notes.trim());
  const confirmLeave = () => !dirty || confirmDiscardUnsaved(locale.startsWith('tr'));
  const clearDuplicate = () => {
    setDuplicateWarning(null);
    setDuplicateId(null);
  };

  const handleSubmit = async () => {
    if (!sourceId || !targetId || !selectedType || duplicateWarning) return;
    const payload = {
      source_entity_type: sourceType,
      source_entity_id: sourceId,
      target_entity_type: targetType,
      target_entity_id: targetId,
      relationship_type: selectedType.value,
      category: selectedType.category,
      notes: notes || undefined,
    };
    setSaveError(null);
    try {
      const duplicates = await relationshipMutations.checkDuplicates(payload);
      if (duplicates.length > 0) {
        setDuplicateId(duplicates[0]?.existing_id ?? null);
        setDuplicateWarning(copy.duplicate);
        return;
      }
    } catch {
      setSaveError(copy.createFailed);
      return;
    }
    setDuplicateWarning(null);
    setDuplicateId(null);
    createMutation.mutate(payload);
  };

  if (authLoading) return <LoadingState label={locale.startsWith('tr') ? 'Yükleniyor…' : 'Loading…'} />;
  if (!canCreate) return <ErrorState title={copy.accessDenied} message={copy.accessDenied} />;

  return (
    <div className="ctc-ds crm-rel-create-form" data-testid="crm-relationships-create">
      <header className="ctc-ds__header">
        <div>
          <Link
            href="/workspaces/crm/relationships"
            data-testid="crm-relationships-create-back"
            onClick={(event) => {
              if (!confirmLeave()) event.preventDefault();
            }}
          >
            {copy.back}
          </Link>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
      </header>

      <section className="crm-rel-create-grid">
        <EntityPicker
          label={copy.source}
          entityType={sourceType}
          entityId={sourceId}
          search={sourceSearch}
          copy={copy}
          onType={(value) => {
            setSourceType(value);
            setSourceId('');
            setSourceName('');
            clearDuplicate();
          }}
          onSearch={setSourceSearch}
          onSelect={(id, name) => {
            setSourceId(id);
            setSourceName(name);
            clearDuplicate();
          }}
        />
        <EntityPicker
          label={copy.target}
          entityType={targetType}
          entityId={targetId}
          search={targetSearch}
          copy={copy}
          onType={(value) => {
            setTargetType(value);
            setTargetId('');
            setTargetName('');
            clearDuplicate();
          }}
          onSearch={setTargetSearch}
          onSelect={(id, name) => {
            setTargetId(id);
            setTargetName(name);
            clearDuplicate();
          }}
        />
      </section>

      <section>
        <Select
          label={copy.type}
          value={selectedType?.value ?? ''}
          onChange={(event) => setRelationshipType(event.target.value)}
          data-testid="crm-relationships-create-type"
        >
          {typeOptions.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </Select>
        <p>{copy.category}: {selectedType ? CATEGORY_LABELS[selectedType.category] || selectedType.category : '—'}</p>
        {sourceName && targetName ? (
          <p>
            {sourceName} → {targetName}
          </p>
        ) : null}
        <label>
          {copy.notes}
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
        </label>
        {duplicateWarning ? (
          <div className="crm-error" role="status" data-testid="crm-relationship-duplicate">
            <p>{duplicateWarning}</p>
            {duplicateId ? (
              <Link href={`/workspaces/crm/relationships/${duplicateId}`}>{copy.openExisting}</Link>
            ) : (
              <button type="button" onClick={() => confirmLeave() && router.push('/workspaces/crm/relationships')}>
                {copy.back}
              </button>
            )}
          </div>
        ) : null}
        {saveError ? (
          <p className="crm-error" role="alert" data-testid="crm-relationship-save-error">
            {saveError}
          </p>
        ) : null}
        <Button
          type="button"
          variant="secondary"
          data-testid="crm-relationships-create-cancel"
          onClick={() => {
            if (confirmLeave()) router.push('/workspaces/crm/relationships');
          }}
        >
          {copy.cancel}
        </Button>
        <Button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={!sourceId || !targetId || !selectedType || Boolean(duplicateWarning) || createMutation.isPending}
          data-testid="crm-relationships-create-submit"
        >
          {copy.submit}
        </Button>
      </section>
    </div>
  );
}
