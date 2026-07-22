'use client';

import { useCallback, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

type Props = {
  companyId: string;
  folderId: string | null;
  onClose: () => void;
  onUpload: (files: File[]) => Promise<unknown>;
  uploading: boolean;
};

export function CompanyDocumentUploadPanel({ onClose, onUpload, uploading }: Props) {
  const t = useTranslations('company.documents.upload');
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useCallback((node: HTMLInputElement | null) => {
    if (node) node.value = '';
  }, []);

  const handleFiles = async (files: FileList | File[]) => {
    setError(null);
    const list = Array.from(files);
    if (list.length === 0) return;
    try {
      await onUpload(list);
    } catch {
      setError(t('error'));
    }
  };

  return (
    <div className="company-doc-upload-overlay" role="dialog" aria-modal="true" aria-labelledby="upload-title">
      <div className="company-doc-upload-panel">
        <header>
          <h2 id="upload-title">{t('title')}</h2>
          <button type="button" onClick={onClose} aria-label={t('close')}>×</button>
        </header>

        <div
          className={`company-doc-dropzone${dragOver ? ' is-dragover' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            void handleFiles(e.dataTransfer.files);
          }}
        >
          <p>{t('dropHint')}</p>
          <input
            ref={inputRef}
            type="file"
            multiple
            onChange={(e) => e.target.files && void handleFiles(e.target.files)}
            disabled={uploading}
          />
        </div>

        {uploading && <p>{t('uploading')}</p>}
        {error && <p className="company-doc-upload-error">{error}</p>}

        <footer>
          <Button variant="secondary" onClick={onClose} disabled={uploading}>{t('cancel')}</Button>
        </footer>
      </div>
    </div>
  );
}
