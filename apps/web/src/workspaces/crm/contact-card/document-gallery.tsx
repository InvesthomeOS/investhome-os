'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Input, Select, TextArea } from '@investhome/ui';

import {
  DOCUMENT_TYPES,
  archiveDocument,
  documentDownloadUrl,
  documentPreviewUrl,
  linkDocument,
  unlinkDocument,
  updateDocument,
  uploadDocuments,
  type DocumentLink,
  type DocumentType,
} from '@/lib/api/documents';
import { useDocumentLabels } from '@/lib/i18n/document-labels';
import { setCrmDocumentVisibility } from '@/workspaces/crm/api/contacts';

const UPLOAD_ERROR_LABELS: Record<string, string> = {
  'documents.errors.missing_extension': 'Dosya türü anlaşılamadı',
  'documents.errors.blocked_type': 'Bu dosya türü engellendi',
  'documents.errors.unsupported_type': 'Desteklenmeyen dosya türü',
  'documents.errors.unknown_type': 'Dosya türü tanınmadı',
  'documents.errors.content_mismatch': 'Dosya içeriği uzantı ile uyuşmuyor',
  'documents.errors.mime_mismatch': 'Dosya türü uyuşmuyor',
  'documents.errors.empty_file': 'Dosya boş',
  'documents.errors.file_too_large': 'Dosya çok büyük',
  'documents.errors.upload_failed': 'Yükleme başarısız',
};

function uploadErrorLabel(code: string | null | undefined): string {
  if (!code) return 'Yükleme başarısız';
  return UPLOAD_ERROR_LABELS[code] || code;
}

export type GalleryDocument = {
  id: string;
  title: string;
  original_file_name?: string | null;
  document_type?: string | null;
  category?: string | null;
  description?: string | null;
  mime_type?: string | null;
  source?: string | null;
  checksum?: string | null;
  bitrix_file_id?: string | null;
  hidden_from_view?: boolean;
  created_at?: string | null;
  file_kind?: string | null;
  file_extension?: string | null;
  links?: DocumentLink[];
};

function isImage(doc: GalleryDocument): boolean {
  const mime = (doc.mime_type || '').toLowerCase();
  const ext = (doc.file_extension || doc.original_file_name || doc.title || '').toLowerCase();
  return mime.startsWith('image/') || /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(ext);
}

function isPdf(doc: GalleryDocument): boolean {
  const mime = (doc.mime_type || '').toLowerCase();
  const ext = (doc.file_extension || doc.original_file_name || doc.title || '').toLowerCase();
  return mime.includes('pdf') || ext.endsWith('.pdf') || (doc.document_type || '').toLowerCase() === 'pdf';
}

export function dedupeGalleryDocuments(items: GalleryDocument[]): GalleryDocument[] {
  const rank = (item: GalleryDocument) =>
    item.source === 'Satış belgesi' || /deal_uf|\buf\b/i.test(item.source || '') ? 0 : 1;
  const seen = new Set<string>();
  const unique: GalleryDocument[] = [];
  for (const item of [...items].sort((a, b) => rank(a) - rank(b))) {
    const tagFile = String(item.bitrix_file_id || '').trim();
    const keys = [
      tagFile ? `bx:${tagFile}` : '',
      item.checksum ? `sum:${item.checksum}` : '',
      `id:${item.id}`,
    ].filter(Boolean);
    if (keys.some((key) => seen.has(key))) continue;
    for (const key of keys) seen.add(key);
    unique.push(item);
  }
  return unique;
}

function usePreviewBlob(doc: GalleryDocument, enabled: boolean) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    if (!enabled) return undefined;
    let objectUrl = '';
    const controller = new AbortController();
    fetch(documentPreviewUrl(doc.id), { credentials: 'include', signal: controller.signal })
      .then((response) => (response.ok ? response.blob() : null))
      .then((blob) => {
        if (!blob) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => undefined);
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [doc.id, enabled]);
  return src;
}

function PreviewThumb({ doc }: { doc: GalleryDocument }) {
  const t = useTranslations('crm.documentGallery');
  const src = usePreviewBlob(doc, isImage(doc));
  if (src) {
    return <img src={src} alt={doc.original_file_name || doc.title} className="crm-doc-gallery__thumb-img" />;
  }
  if (isPdf(doc)) return <span className="crm-doc-gallery__icon">PDF</span>;
  if (isImage(doc)) return <span className="crm-doc-gallery__icon">{t('image')}</span>;
  return <span className="crm-doc-gallery__icon">{t('file')}</span>;
}

export function PreviewBody({ doc }: { doc: GalleryDocument }) {
  const t = useTranslations('crm.documentGallery');
  const src = usePreviewBlob(doc, isImage(doc) || isPdf(doc));
  if (src && isImage(doc)) {
    return <img src={src} alt={doc.original_file_name || doc.title} />;
  }
  if (src && isPdf(doc)) {
    return <iframe title={doc.title} src={src} />;
  }
  if (isImage(doc) || isPdf(doc)) return <p>{t('previewLoading')}</p>;
  return (
    <p>
      {t('noPreview')} <a href={documentDownloadUrl(doc.id)}>{t('downloadOpen')}</a>
    </p>
  );
}

export function DocumentPreviewDialog({
  doc,
  onClose,
}: {
  doc: GalleryDocument;
  onClose: () => void;
}) {
  const tCommon = useTranslations('common');
  return (
    <div className="crm-doc-gallery__modal" data-testid="crm-doc-preview-modal" role="dialog">
      <div className="crm-doc-gallery__modal-panel">
        <header>
          <strong>{doc.original_file_name || doc.title}</strong>
          <Button type="button" size="sm" variant="secondary" onClick={onClose}>
            {tCommon('close')}
          </Button>
        </header>
        <PreviewBody doc={doc} />
      </div>
    </div>
  );
}

function entityLink(doc: GalleryDocument, entityType: string, entityId: string): DocumentLink | undefined {
  return (doc.links ?? []).find(
    (link) =>
      link.entity_id === entityId &&
      (link.entity_type === entityType ||
        (entityType === 'crm_contact' && link.entity_type === 'contact') ||
        (entityType === 'contact' && link.entity_type === 'crm_contact') ||
        (entityType === 'crm_agreement' && link.entity_type === 'agreement')),
  );
}

export function DocumentGallery({
  documents,
  entityType,
  entityId,
  onChanged,
  canUpload = false,
  canEditMeta = false,
  canUnlink = false,
  canArchive = false,
}: {
  documents: GalleryDocument[];
  entityType: string;
  entityId: string;
  onChanged: () => void;
  canUpload?: boolean;
  canEditMeta?: boolean;
  canUnlink?: boolean;
  canArchive?: boolean;
}) {
  const t = useTranslations('crm.documentGallery');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getTypeLabel } = useDocumentLabels();
  const [showHidden, setShowHidden] = useState(false);
  const [preview, setPreview] = useState<GalleryDocument | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ kind: 'unlink' | 'archive'; doc: GalleryDocument } | null>(null);
  const [editing, setEditing] = useState<GalleryDocument | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editType, setEditType] = useState<DocumentType>('other');
  const [editCategory, setEditCategory] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const unique = useMemo(() => dedupeGalleryDocuments(documents), [documents]);
  const visible = unique.filter((item) => showHidden || !item.hidden_from_view);
  const hiddenCount = unique.filter((item) => item.hidden_from_view).length;

  const run = async (docId: string, work: () => Promise<void>) => {
    setBusyId(docId);
    setError(null);
    try {
      await work();
      onChanged();
    } catch {
      setError(t('actionFailed'));
    } finally {
      setBusyId(null);
    }
  };

  const toggleHidden = (doc: GalleryDocument, hidden: boolean) =>
    run(doc.id, () =>
      setCrmDocumentVisibility({
        document_id: doc.id,
        entity_type: entityType,
        entity_id: entityId,
        hidden,
      }).then(() => undefined),
    );

  const submitUpload = async (fileList: FileList | null) => {
    if (!fileList?.length || !canUpload) return;
    setUploading(true);
    setError(null);
    try {
      const results = await uploadDocuments(Array.from(fileList), {
        document_type: 'other',
      });
      const failures: string[] = [];
      for (const result of results) {
        if (!result.success || !result.document) {
          failures.push(`${result.file_name}: ${uploadErrorLabel(result.error)}`);
          continue;
        }
        try {
          await linkDocument(result.document.id, entityType, entityId);
        } catch {
          failures.push(`${result.file_name}: ${t('uploadFailed')}`);
        }
      }
      if (failures.length) setError(failures.join(' · '));
      if (results.some((result) => result.success && result.document)) onChanged();
    } catch {
      setError(t('uploadFailed'));
    } finally {
      setUploading(false);
    }
  };

  const saveMeta = async () => {
    if (!editing || !canEditMeta) return;
    await run(editing.id, async () => {
      await updateDocument(editing.id, {
        title: editTitle.trim() || editing.title,
        document_type: editType,
        category: editCategory.trim() || null,
        description: editDescription.trim() || null,
      });
      setEditing(null);
    });
  };

  const applyConfirm = async () => {
    if (!confirm) return;
    const doc = confirm.doc;
    const kind = confirm.kind;
    setConfirm(null);
    if (kind === 'unlink') {
      const link = entityLink(doc, entityType, entityId);
      if (!link) {
        setError(t('notLinked'));
        return;
      }
      await run(doc.id, () => unlinkDocument(doc.id, link.id));
      return;
    }
    await run(doc.id, async () => {
      await archiveDocument(doc.id);
    });
  };

  return (
    <div className="crm-doc-gallery" data-testid="crm-document-gallery">
      <div className="crm-doc-gallery__tools">
        {canUpload ? (
          <label className="crm-doc-gallery__upload">
            <input
              type="file"
              multiple
              data-testid="contact-document-upload"
              disabled={uploading}
              onChange={(event) => {
                void submitUpload(event.target.files);
                event.currentTarget.value = '';
              }}
            />
            <span>{uploading ? tCommon('loading') : 'Belge Ekle'}</span>
          </label>
        ) : null}
        {hiddenCount ? (
          <Button type="button" size="sm" variant="secondary" onClick={() => setShowHidden((value) => !value)}>
            {showHidden ? t('hideHidden') : t('showHidden')} ({hiddenCount})
          </Button>
        ) : null}
      </div>
      {error ? <p className="crm-verify-detail__error">{error}</p> : null}
      {!visible.length ? <p>{t('empty')}</p> : null}
      <ul className="crm-doc-gallery__list">
        {visible.map((doc) => (
          <li
            key={doc.id}
            className={`crm-doc-gallery__item${doc.hidden_from_view ? ' is-hidden' : ''}`}
            data-testid={`crm-doc-${doc.id}`}
          >
            <button
              type="button"
              className="crm-doc-gallery__thumb"
              onClick={() => setPreview(doc)}
              data-testid={`crm-doc-preview-${doc.id}`}
            >
              <PreviewThumb doc={doc} />
            </button>
            <div className="crm-doc-gallery__meta">
              <strong>{doc.original_file_name || doc.title}</strong>
              <small>
                {[
                  doc.document_type ? getTypeLabel(doc.document_type) : null,
                  doc.category,
                  doc.source,
                  doc.created_at ? new Date(doc.created_at).toLocaleDateString(locale) : null,
                  doc.hidden_from_view ? t('hidden') : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </small>
              <div className="crm-doc-gallery__actions">
                <button type="button" onClick={() => setPreview(doc)}>
                  {t('open')}
                </button>
                <a href={documentDownloadUrl(doc.id)}>{tCommon('download')}</a>
                {canEditMeta ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-edit-${doc.id}`}
                    onClick={() => {
                      setEditing(doc);
                      setEditTitle(doc.title || doc.original_file_name || '');
                      setEditType((DOCUMENT_TYPES as readonly string[]).includes(doc.document_type || '')
                        ? (doc.document_type as DocumentType)
                        : 'other');
                      setEditCategory(doc.category || '');
                      setEditDescription(doc.description || '');
                    }}
                  >
                    {t('editInfo')}
                  </button>
                ) : null}
                {doc.hidden_from_view ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-restore-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => void toggleHidden(doc, false)}
                  >
                    {t('restore')}
                  </button>
                ) : (
                  <button
                    type="button"
                    data-testid={`crm-doc-hide-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => void toggleHidden(doc, true)}
                  >
                    {t('hideFromView')}
                  </button>
                )}
                {canUnlink && entityLink(doc, entityType, entityId) ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-unlink-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => setConfirm({ kind: 'unlink', doc })}
                  >
                    {t('unlink')}
                  </button>
                ) : null}
                {canArchive ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-archive-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => setConfirm({ kind: 'archive', doc })}
                  >
                    {t('archive')}
                  </button>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {preview ? <DocumentPreviewDialog doc={preview} onClose={() => setPreview(null)} /> : null}
      {editing ? (
        <div className="crm-doc-gallery__modal" role="dialog" data-testid="crm-doc-edit-modal">
          <div className="crm-doc-gallery__modal-panel">
            <header>
              <strong>{t('infoTitle')}</strong>
              <Button type="button" size="sm" variant="secondary" onClick={() => setEditing(null)}>
                {tCommon('cancel')}
              </Button>
            </header>
            <Input label={t('name')} value={editTitle} onChange={(event) => setEditTitle(event.target.value)} />
            <Select label={t('type')} value={editType} onChange={(event) => setEditType(event.target.value as DocumentType)}>
              {DOCUMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {getTypeLabel(type)}
                </option>
              ))}
            </Select>
            <Input label={t('category')} value={editCategory} onChange={(event) => setEditCategory(event.target.value)} />
            <TextArea
              label={t('description')}
              value={editDescription}
              onChange={(event) => setEditDescription(event.target.value)}
            />
            <Button type="button" size="sm" disabled={busyId === editing.id} onClick={() => void saveMeta()}>
              {tCommon('save')}
            </Button>
          </div>
        </div>
      ) : null}
      {confirm ? (
        <div className="crm-doc-gallery__modal" role="alertdialog" data-testid="crm-doc-confirm-modal">
          <div className="crm-doc-gallery__modal-panel">
            <header>
              <strong>{confirm.kind === 'archive' ? t('archiveTitle') : t('unlinkTitle')}</strong>
            </header>
            <p>
              {confirm.kind === 'archive' ? t('archiveBody') : t('unlinkBody')}
            </p>
            <div className="crm-doc-gallery__actions">
              <Button type="button" size="sm" variant="secondary" onClick={() => setConfirm(null)}>
                {tCommon('cancel')}
              </Button>
              <Button type="button" size="sm" data-testid="crm-doc-confirm" onClick={() => void applyConfirm()}>
                {tCommon('confirm')}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
