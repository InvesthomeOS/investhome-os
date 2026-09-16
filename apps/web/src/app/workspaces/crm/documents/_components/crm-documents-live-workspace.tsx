'use client';

import { useMemo, useState } from 'react';
import type { Route } from 'next';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, LoadingState } from '@investhome/ui';

import { documentDownloadUrl, fetchDocuments, type Document } from '@/lib/api/documents';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';

import './ds/documents-ds.css';

const PAGE_SIZE = 25;

const COPY = {
  tr: {
    title: 'Belgeler',
    subtitle: 'Mevcut belge ve Drive bağlantıları. Yükleme altyapısı bu sayfada yok.',
    search: 'Belge ara',
    emptyTitle: 'Bağlı belge yok',
    empty: 'Bu görünümde gösterilecek gerçek belge kaydı yok.',
    name: 'Belge',
    related: 'İlgili kayıt',
    type: 'Tür',
    source: 'Kaynak',
    date: 'Güncelleme',
    open: 'Aç',
    previous: 'Önceki',
    next: 'Sonraki',
    contact: 'Kişi',
    company: 'Şirket',
    project: 'Proje',
    all: 'Tümü',
  },
  en: {
    title: 'Documents',
    subtitle: 'Existing document and Drive links. This page does not add upload storage.',
    search: 'Search documents',
    emptyTitle: 'No linked documents',
    empty: 'There are no real documents to show in this view.',
    name: 'Document',
    related: 'Related record',
    type: 'Type',
    source: 'Source',
    date: 'Updated',
    open: 'Open',
    previous: 'Previous',
    next: 'Next',
    contact: 'Contact',
    company: 'Company',
    project: 'Project',
    all: 'All',
  },
} as const;

type RelatedHit = {
  kind: 'contact' | 'company' | 'project' | 'other';
  id: string;
  label: string;
};

function relatedHits(doc: Document): RelatedHit[] {
  const hits: RelatedHit[] = [];
  const push = (kind: RelatedHit['kind'], id: string | null, label: string) => {
    if (!id || hits.some((hit) => hit.id === id && hit.kind === kind)) return;
    hits.push({ kind, id, label });
  };

  push('company', doc.company_id, doc.related_record_label || 'company');
  push('project', doc.project_id, doc.related_record_label || 'project');

  for (const link of doc.links ?? []) {
    const type = link.entity_type.toLowerCase();
    if (type === 'contact' || type === 'crm_contact') {
      push('contact', link.entity_id, doc.related_record_label || 'contact');
    } else if (type === 'company' || type === 'crm_company') {
      push('company', link.entity_id, doc.related_record_label || 'company');
    } else if (type === 'project') {
      push('project', link.entity_id, doc.related_record_label || 'project');
    } else {
      push('other', link.entity_id, doc.related_record_label || link.entity_type);
    }
  }
  return hits;
}

export function CrmDocumentsLiveWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const router = useRouter();
  const { openContact } = useContactCard();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const listQuery = useQuery({
    queryKey: ['crm', 'documents', 'live', search, page],
    queryFn: () =>
      fetchDocuments({
        search: search.trim() || undefined,
        page,
        page_size: PAGE_SIZE,
        sort_by: 'updated_at',
        sort_dir: 'desc',
      }),
  });

  const items = useMemo(
    () => (listQuery.data?.items ?? []).filter((doc) => !doc.is_demo),
    [listQuery.data?.items],
  );
  const hiddenDemo = (listQuery.data?.items ?? []).length - items.length;
  const total = Math.max(0, (listQuery.data?.total ?? 0) - hiddenDemo);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const openRelated = (hit: RelatedHit) => {
    if (hit.kind === 'contact') {
      openContact(hit.id);
      return;
    }
    if (hit.kind === 'company') {
      router.push(`/workspaces/crm/companies/${hit.id}` as Route);
      return;
    }
    if (hit.kind === 'project') {
      router.push(`/dashboard/projects/${hit.id}` as Route);
    }
  };

  if (listQuery.isLoading) {
    return <LoadingState label={copy.title} />;
  }

  return (
    <div className="documents-ds" data-testid="crm-documents-live">
      <header className="documents-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <span className="documents-ds__count">{total}</span>
      </header>

      <section className="documents-ds__toolbar">
        <Input
          label={copy.search}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder={copy.search}
        />
      </section>

      {items.length === 0 ? (
        <div className="documents-ds__empty">
          <strong>{copy.emptyTitle}</strong>
          <p>{copy.empty}</p>
        </div>
      ) : (
        <div className="documents-ds__table-wrap">
          <table className="documents-ds__table">
            <thead>
              <tr>
                <th>{copy.name}</th>
                <th>{copy.related}</th>
                <th>{copy.type}</th>
                <th>{copy.source}</th>
                <th>{copy.date}</th>
                <th>{copy.open}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((doc) => {
                const related = relatedHits(doc);
                return (
                  <tr key={doc.id}>
                    <td>{doc.title || doc.original_file_name}</td>
                    <td>
                      {related.length === 0 ? (
                        '—'
                      ) : (
                        <div className="documents-ds__related">
                          {related.map((hit) =>
                            hit.kind === 'other' ? (
                              <span key={`${hit.kind}-${hit.id}`}>{hit.label}</span>
                            ) : (
                              <button
                                key={`${hit.kind}-${hit.id}`}
                                type="button"
                                className="documents-ds__link"
                                onClick={() => openRelated(hit)}
                              >
                                {hit.label}
                              </button>
                            ),
                          )}
                        </div>
                      )}
                    </td>
                    <td>{doc.document_type}</td>
                    <td>{doc.storage_provider}</td>
                    <td>{new Date(doc.updated_at || doc.created_at).toLocaleString(locale)}</td>
                    <td>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => window.open(documentDownloadUrl(doc.id), '_blank', 'noopener')}
                      >
                        {copy.open}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="documents-ds__pagination">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          {copy.previous}
        </Button>
        <span>
          {page} / {pages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= pages}
          onClick={() => setPage((p) => p + 1)}
        >
          {copy.next}
        </Button>
      </div>
    </div>
  );
}
