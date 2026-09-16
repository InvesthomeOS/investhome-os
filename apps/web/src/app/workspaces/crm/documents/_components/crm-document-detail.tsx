'use client';

import { useState } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, LoadingState } from '@investhome/ui';

import { documentDownloadUrl, fetchDocument } from '@/lib/api/documents';
import {
  CrmDetailMetaGrid,
  CrmEntityDetailShell,
} from '../../_components/crm-entity-detail-shell';
import '../../_components/crm-entity-detail.css';
import '../documents.css';

const COPY = {
  tr: {
    back: 'Belgelere dön',
    eyebrow: 'Belge',
    notFoundTitle: 'Belge bulunamadı',
    notFoundDescription: 'Bu kayıt mevcut belge arşivinde yok veya demo belgedir.',
    open: 'Aç',
    type: 'Tür',
    source: 'Kaynak',
    related: 'İlgili kayıt',
    created: 'Oluşturma',
    updated: 'Güncelleme',
    metadata: 'Bilgi',
  },
  en: {
    back: 'Back to documents',
    eyebrow: 'Document',
    notFoundTitle: 'Document not found',
    notFoundDescription: 'This record is missing from the live archive or is a demo document.',
    open: 'Open',
    type: 'Type',
    source: 'Source',
    related: 'Related record',
    created: 'Created',
    updated: 'Updated',
    metadata: 'Details',
  },
} as const;

export function CrmDocumentDetailView({
  documentId,
  listHref = '/workspaces/crm/documents',
}: {
  documentId: string;
  listHref?: string;
}) {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const [tab, setTab] = useState('metadata');
  const query = useQuery({
    queryKey: ['crm', 'documents', 'detail', documentId],
    queryFn: () => fetchDocument(documentId),
    enabled: Boolean(documentId),
  });

  if (query.isLoading) {
    return <LoadingState label={copy.eyebrow} />;
  }

  const doc = query.data;
  if (!doc || doc.is_demo) {
    return <EmptyState title={copy.notFoundTitle} description={copy.notFoundDescription} />;
  }

  return (
    <CrmEntityDetailShell
      testId="crm-document-detail"
      backHref={listHref}
      backLabel={copy.back}
      title={doc.title || doc.original_file_name}
      subtitle={doc.related_record_label || doc.storage_provider}
      eyebrow={copy.eyebrow}
      tabs={[{ id: 'metadata', label: copy.metadata }]}
      activeTab={tab}
      onTabChange={setTab}
    >
      <CrmDetailMetaGrid
        items={[
          { label: copy.type, value: doc.document_type },
          { label: copy.source, value: doc.storage_provider },
          { label: copy.related, value: doc.related_record_label || '—' },
          { label: copy.created, value: new Date(doc.created_at).toLocaleString(locale) },
          { label: copy.updated, value: new Date(doc.updated_at).toLocaleString(locale) },
        ]}
      />
      <Button
        size="sm"
        variant="secondary"
        onClick={() => window.open(documentDownloadUrl(doc.id), '_blank', 'noopener')}
      >
        {copy.open}
      </Button>
    </CrmEntityDetailShell>
  );
}
