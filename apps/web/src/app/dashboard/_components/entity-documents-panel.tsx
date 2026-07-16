'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { DocumentUploadPanel } from '@/app/dashboard/documents/_components/document-upload-panel';
import { fetchDocumentsByEntity, type Document } from '@/lib/api/documents';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useDocumentLabels } from '@/lib/i18n/document-labels';

interface EntityDocumentsPanelProps {
  entityType: 'lead' | 'investor' | 'project' | 'transaction' | 'user' | 'inventory_asset';
  entityId: string;
  projectId?: string;
  investorId?: string;
  leadId?: string;
  transactionId?: string;
}

export function EntityDocumentsPanel({
  entityType,
  entityId,
  projectId,
  investorId,
  leadId,
  transactionId,
}: EntityDocumentsPanelProps) {
  const t = useTranslations('documents');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const { getTypeLabel } = useDocumentLabels();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);

  const canView = user ? hasPermission(user, 'documents', 'view') : false;
  const canCreate = user ? hasPermission(user, 'documents', 'create') : false;

  const load = useCallback(async () => {
    if (!canView) {
      setDocuments([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await fetchDocumentsByEntity(entityType, entityId);
      setDocuments(response.items);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [canView, entityType, entityId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!canView) return null;

  return (
    <section className="entity-documents-panel">
      <div className="entity-documents-panel__header">
        <h3>{t('entitySectionTitle')}</h3>
        {canCreate && (
          <button type="button" className="leads__button leads__button--secondary" onClick={() => setShowUpload(true)}>
            {t('uploadDocuments')}
          </button>
        )}
      </div>

      {loading ? (
        <p>{tCommon('loading')}</p>
      ) : documents.length === 0 ? (
        <p>{t('entityEmpty')}</p>
      ) : (
        <ul className="entity-documents-panel__list">
          {documents.map((doc) => (
            <li key={doc.id}>
              <strong>{doc.title}</strong>
              <span>{getTypeLabel(doc.document_type)} · v{doc.version_number}</span>
            </li>
          ))}
        </ul>
      )}

      {showUpload && (
        <DocumentUploadPanel
          projectId={projectId}
          investorId={investorId}
          leadId={leadId}
          transactionId={transactionId}
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            void load();
          }}
        />
      )}
    </section>
  );
}
