'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  DocumentDetailActivity,
  DocumentDetailRelated,
  DocumentDetailVersions,
  DocumentNotFound,
} from '../../_components/documents/document-detail-sections';
import {
  DocumentDetailHeader,
  DocumentDetailMetadata,
} from '../../_components/documents/document-detail-header';
import { DocumentPreview } from '../../_components/documents/document-preview';
import { DemonstrationBanner } from '../../_components/documents/demonstration-banner';
import { getDocumentById } from '../../_data/documents';
import { createMockDownloadBlob } from '../../_data/document-calculations';
import type { InvestorDocument } from '../../_data/document-types';
import { getSignatureRequestByDocumentId } from '../../_data/signature-requests';
import { useDocumentsState } from '../../_state/documents-state';
import Link from 'next/link';
import type { Route } from 'next';

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const { documents, markAsRead, archiveDocument } = useDocumentsState();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    void params.then((p) => setDocumentId(p.documentId));
  }, [params]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(t);
  }, [toast]);

  const doc = useMemo(() => {
    if (!documentId) return undefined;
    return documents.find((d) => d.id === documentId) ?? getDocumentById(documentId);
  }, [documents, documentId]);

  const relatedDocs = useMemo(() => {
    if (!doc) return [];
    return documents.filter((d: InvestorDocument) => doc.relatedDocumentIds.includes(d.id));
  }, [doc, documents]);

  const signatureRequest = useMemo(
    () => (doc?.signatureRequestId ? getSignatureRequestByDocumentId(doc.id) : undefined),
    [doc],
  );

  useEffect(() => {
    if (doc && !doc.isRead) markAsRead(doc.id);
  }, [doc, markAsRead]);

  const handleDownload = useCallback(() => {
    if (!doc) return;
    const blob = createMockDownloadBlob(doc);
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement('a');
    a.href = url;
    a.download = `${doc.fileName.replace(/\.[^.]+$/, '')}-demo.json`;
    a.click();
    URL.revokeObjectURL(url);
    setToast(`Download started: ${doc.fileName} (demo placeholder)`);
  }, [doc]);

  if (!documentId) return null;
  if (!doc) return <DocumentNotFound />;

  return (
    <div className="investor-page inv-docs inv-docs--detail">
      <DemonstrationBanner compact />
      <DocumentDetailHeader
        document={doc}
        onPreview={() => setPreviewOpen(true)}
        onDownload={handleDownload}
        onArchive={() => {
          archiveDocument(doc.id);
          setToast('Document archived (demo — soft delete).');
        }}
      />

      <div className="inv-docs__detail-layout">
        <div className="inv-docs__detail-main">
          <DocumentDetailMetadata document={doc} />
          <DocumentDetailVersions document={doc} />
          <DocumentDetailActivity document={doc} />
          <DocumentDetailRelated document={doc} relatedDocuments={relatedDocs} />
        </div>

        <aside className="inv-docs__detail-sidebar">
          {signatureRequest ? (
            <section className="inv-docs__detail-panel">
              <h2>Signature Status</h2>
              <p>{signatureRequest.status.replace(/_/g, ' ')}</p>
              {doc.requiresSignature && signatureRequest.status === 'action_required' ? (
                <Link
                  href={`/investor/signatures/${signatureRequest.id}/sign` as Route}
                  className="inv-docs__btn inv-docs__btn--primary"
                >
                  Review & Sign
                </Link>
              ) : null}
            </section>
          ) : null}
        </aside>
      </div>

      <DocumentPreview
        document={doc}
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        onDownload={handleDownload}
        onMarkRead={markAsRead}
      />

      {toast ? (
        <div className="inv-investments__toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}
    </div>
  );
}
