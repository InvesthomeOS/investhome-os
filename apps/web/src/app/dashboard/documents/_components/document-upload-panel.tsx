'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  uploadDocuments,
  type ConfidentialityLevel,
  type DocumentType,
} from '@/lib/api/documents';
import { useDocumentLabels } from '@/lib/i18n/document-labels';

interface DocumentUploadPanelProps {
  onClose: () => void;
  onUploaded: () => void;
  projectId?: string;
  investorId?: string;
  leadId?: string;
  transactionId?: string;
}

interface UploadItem {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function DocumentUploadPanel({
  onClose,
  onUploaded,
  projectId,
  investorId,
  leadId,
  transactionId,
}: DocumentUploadPanelProps) {
  const t = useTranslations('documents');
  const tCommon = useTranslations('common');
  const { typeOptions, confidentialityOptions } = useDocumentLabels();
  const [items, setItems] = useState<UploadItem[]>([]);
  const [title, setTitle] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType>('other');
  const [category, setCategory] = useState('');
  const [confidentiality, setConfidentiality] = useState<ConfidentialityLevel>('internal');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    setItems(Array.from(fileList).map((file) => ({ file, status: 'pending' as const })));
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    handleFiles(event.dataTransfer.files);
  };

  const handleUpload = async () => {
    if (items.length === 0) return;
    setSubmitting(true);
    try {
      const results = await uploadDocuments(
        items.map((item) => item.file),
        {
          title: title || undefined,
          document_type: documentType,
          category: category || undefined,
          confidentiality_level: confidentiality,
          description: description || undefined,
          tags: tags || undefined,
          project_id: projectId,
          investor_id: investorId,
          lead_id: leadId,
          transaction_id: transactionId,
        },
      );
      setItems((prev) =>
        prev.map((item, index) => {
          const result = results[index];
          if (!result) return { ...item, status: 'error', error: t('upload.failed') };
          return {
            ...item,
            status: result.success ? 'success' : 'error',
            error: result.error ?? undefined,
          };
        }),
      );
      if (results.every((r) => r.success)) {
        onUploaded();
      }
    } catch {
      setItems((prev) => prev.map((item) => ({ ...item, status: 'error', error: t('upload.failed') })));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="leads-modal" role="presentation" onClick={onClose}>
      <div className="leads-modal__panel documents-upload-panel" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="leads-modal__header">
          <h2>{t('upload.title')}</h2>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>{tCommon('close')}</button>
        </header>

        <div
          className="documents-upload-dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <p>{t('upload.dropHint')}</p>
          <input type="file" multiple onChange={(e) => handleFiles(e.target.files)} />
        </div>

        <div className="leads-form__grid">
          <label>
            <span>{t('upload.formTitle')}</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            <span>{t('upload.documentType')}</span>
            <select value={documentType} onChange={(e) => setDocumentType(e.target.value as DocumentType)}>
              {typeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('upload.category')}</span>
            <input value={category} onChange={(e) => setCategory(e.target.value)} />
          </label>
          <label>
            <span>{t('upload.confidentiality')}</span>
            <select value={confidentiality} onChange={(e) => setConfidentiality(e.target.value as ConfidentialityLevel)}>
              {confidentialityOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label className="leads-form__full">
            <span>{t('upload.description')}</span>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </label>
          <label>
            <span>{t('upload.tags')}</span>
            <input value={tags} onChange={(e) => setTags(e.target.value)} />
          </label>
        </div>

        {items.length > 0 && (
          <ul className="documents-upload-list">
            {items.map((item) => (
              <li key={item.file.name}>
                <span>{item.file.name}</span>
                <span>{t(`upload.status.${item.status}`)}</span>
                {item.error && <span className="documents-upload-list__error">{item.error}</span>}
              </li>
            ))}
          </ul>
        )}

        <footer className="leads-modal__footer">
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>{tCommon('cancel')}</button>
          <button type="button" className="leads__button leads__button--primary" disabled={submitting || items.length === 0} onClick={() => void handleUpload()}>
            {submitting ? t('upload.uploading') : t('upload.submit')}
          </button>
        </footer>
      </div>
    </div>
  );
}
