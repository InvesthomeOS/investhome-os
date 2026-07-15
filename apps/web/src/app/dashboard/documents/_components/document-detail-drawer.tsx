'use client';

import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import {
  documentDownloadUrl,
  documentPreviewUrl,
  fetchDocumentVersions,
  formatDocumentDate,
  formatFileSize,
  type Document,
  type DocumentVersion,
} from '@/lib/api/documents';
import { useDocumentLabels } from '@/lib/i18n/document-labels';

interface DocumentDetailDrawerProps {
  document: Document | null;
  archiving: boolean;
  canArchive: boolean;
  canDownload: boolean;
  onClose: () => void;
  onArchive: (document: Document) => void;
  onRefresh: () => void;
}

export function DocumentDetailDrawer({
  document,
  archiving,
  canArchive,
  canDownload,
  onClose,
  onArchive,
}: DocumentDetailDrawerProps) {
  const t = useTranslations('documents');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getTypeLabel, getStatusLabel, getConfidentialityLabel } = useDocumentLabels();
  const [versions, setVersions] = useState<DocumentVersion[]>([]);

  useEffect(() => {
    if (!document) {
      setVersions([]);
      return;
    }
    void fetchDocumentVersions(document.id)
      .then((response) => setVersions(response.items))
      .catch(() => setVersions([]));
  }, [document]);

  if (!document) return null;

  return (
    <div className="leads-drawer" role="presentation" onClick={onClose}>
      <aside className="leads-drawer__panel documents-drawer" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="leads-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
            <h2>{document.title}</h2>
            {document.is_demo && <span className="leads__demo-tag">{tCommon('demoData')}</span>}
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>{tCommon('close')}</button>
        </header>

        {document.is_previewable && canDownload ? (
          <div className="documents-preview">
            {document.file_extension === 'txt' || document.file_extension === 'csv' ? (
              <iframe title={document.title} src={documentPreviewUrl(document.id)} className="documents-preview__frame" />
            ) : (
              <iframe title={document.title} src={documentPreviewUrl(document.id)} className="documents-preview__frame" />
            )}
          </div>
        ) : (
          <div className="documents-preview documents-preview--unavailable">
            <p>{t('previewUnavailable')}</p>
            <p>{document.original_file_name} · {formatFileSize(document.file_size, locale)}</p>
          </div>
        )}

        <dl className="leads-drawer__grid">
          <div><dt>{t('columns.type')}</dt><dd>{getTypeLabel(document.document_type)}</dd></div>
          <div><dt>{t('columns.status')}</dt><dd>{getStatusLabel(document.status)}</dd></div>
          <div><dt>{t('columns.confidentiality')}</dt><dd>{getConfidentialityLabel(document.confidentiality_level)}</dd></div>
          <div><dt>{t('columns.version')}</dt><dd>v{document.version_number}</dd></div>
          <div><dt>{t('columns.relatedRecord')}</dt><dd>{document.related_record_label ?? tCommon('noValue')}</dd></div>
          <div><dt>{t('columns.uploadedBy')}</dt><dd>{document.uploaded_by_name ?? tCommon('noValue')}</dd></div>
          <div><dt>{t('columns.documentDate')}</dt><dd>{formatDocumentDate(document.document_date, locale)}</dd></div>
          <div><dt>{t('columns.updatedDate')}</dt><dd>{formatDocumentDate(document.updated_at, locale)}</dd></div>
        </dl>

        {document.description && (
          <div className="leads-drawer__notes">
            <h3>{t('upload.description')}</h3>
            <p>{document.description}</p>
          </div>
        )}

        <section className="documents-versions">
          <h3>{t('versionHistory')}</h3>
          {versions.length === 0 ? (
            <p>{t('noVersions')}</p>
          ) : (
            <ul>
              {versions.map((version) => (
                <li key={version.id}>
                  <strong>v{version.version_number}</strong> — {version.original_file_name}
                  <span>{formatDocumentDate(version.created_at, locale)}</span>
                  {version.version_notes && <em>{version.version_notes}</em>}
                </li>
              ))}
            </ul>
          )}
        </section>

        {document.links.length > 0 && (
          <section className="documents-related">
            <h3>{t('relatedRecords')}</h3>
            <ul>
              {document.links.map((link) => (
                <li key={link.id}>{link.entity_type}: {link.entity_id}</li>
              ))}
            </ul>
          </section>
        )}

        <EntityActivityTimeline entityType="document" entityId={document.id} title={t('activityTitle')} />

        <footer className="leads-drawer__footer">
          {canDownload && (
            <a className="leads__button leads__button--secondary" href={documentDownloadUrl(document.id)} target="_blank" rel="noreferrer">
              {t('download')}
            </a>
          )}
          {canArchive && (
            <button type="button" className="leads__button leads__button--danger" disabled={archiving} onClick={() => onArchive(document)}>
              {document.archived_at ? t('restore') : t('archive')}
            </button>
          )}
        </footer>
      </aside>
    </div>
  );
}
