'use client';

import { useEffect, useMemo, useState } from 'react';

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
import { setCrmDocumentVisibility } from '@/workspaces/crm/api/contacts';

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
  const src = usePreviewBlob(doc, isImage(doc));
  if (src) {
    return <img src={src} alt={doc.original_file_name || doc.title} className="crm-doc-gallery__thumb-img" />;
  }
  if (isPdf(doc)) return <span className="crm-doc-gallery__icon">PDF</span>;
  if (isImage(doc)) return <span className="crm-doc-gallery__icon">GÖRSEL</span>;
  return <span className="crm-doc-gallery__icon">DOSYA</span>;
}

export function PreviewBody({ doc }: { doc: GalleryDocument }) {
  const src = usePreviewBlob(doc, isImage(doc) || isPdf(doc));
  if (src && isImage(doc)) {
    return <img src={src} alt={doc.original_file_name || doc.title} />;
  }
  if (src && isPdf(doc)) {
    return <iframe title={doc.title} src={src} />;
  }
  if (isImage(doc) || isPdf(doc)) return <p>Önizleme yükleniyor…</p>;
  return (
    <p>
      Bu dosya türü için önizleme yok. <a href={documentDownloadUrl(doc.id)}>İndir / aç</a>
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
  return (
    <div className="crm-doc-gallery__modal" data-testid="crm-doc-preview-modal" role="dialog">
      <div className="crm-doc-gallery__modal-panel">
        <header>
          <strong>{doc.original_file_name || doc.title}</strong>
          <Button type="button" size="sm" variant="secondary" onClick={onClose}>
            Kapat
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
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadType, setUploadType] = useState<DocumentType>('other');
  const [uploadDescription, setUploadDescription] = useState('');
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Belge işlemi başarısız');
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
        title: uploadTitle.trim() || undefined,
        document_type: uploadType,
        description: uploadDescription.trim() || undefined,
      });
      for (const result of results) {
        if (!result.success || !result.document) {
          throw new Error(result.error || 'Yükleme başarısız');
        }
        await linkDocument(result.document.id, entityType, entityId);
      }
      setUploadTitle('');
      setUploadDescription('');
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Yükleme başarısız');
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
        setError('Bu belge bu kayda bağlı değil');
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
            <span>{uploading ? 'Yükleniyor…' : 'Belge yükle'}</span>
          </label>
        ) : null}
        <Button type="button" size="sm" variant="secondary" onClick={() => setShowHidden((value) => !value)}>
          {showHidden ? 'Gizlenenleri Gizle' : 'Gizlenenleri Göster'}
          {hiddenCount ? ` (${hiddenCount})` : ''}
        </Button>
      </div>
      {canUpload ? (
        <div className="crm-contact-card__panel-grid">
          <Input label="Belge adı" value={uploadTitle} onChange={(event) => setUploadTitle(event.target.value)} />
          <Select
            label="Tür"
            value={uploadType}
            onChange={(event) => setUploadType(event.target.value as DocumentType)}
          >
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </Select>
          <TextArea
            label="Açıklama"
            value={uploadDescription}
            onChange={(event) => setUploadDescription(event.target.value)}
          />
        </div>
      ) : null}
      {error ? <p className="crm-verify-detail__error">{error}</p> : null}
      {!visible.length ? <p>Bu görünümde belge yok.</p> : null}
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
                  doc.document_type,
                  doc.category,
                  doc.source,
                  doc.created_at ? new Date(doc.created_at).toLocaleDateString('tr-TR') : null,
                  doc.hidden_from_view ? 'Gizli' : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </small>
              <div className="crm-doc-gallery__actions">
                <button type="button" onClick={() => setPreview(doc)}>
                  Aç
                </button>
                <a href={documentDownloadUrl(doc.id)}>İndir</a>
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
                    Bilgileri düzenle
                  </button>
                ) : null}
                {doc.hidden_from_view ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-restore-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => void toggleHidden(doc, false)}
                  >
                    Geri Getir
                  </button>
                ) : (
                  <button
                    type="button"
                    data-testid={`crm-doc-hide-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => void toggleHidden(doc, true)}
                  >
                    Görünümden Kaldır
                  </button>
                )}
                {canUnlink && entityLink(doc, entityType, entityId) ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-unlink-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => setConfirm({ kind: 'unlink', doc })}
                  >
                    Kişiden kaldır
                  </button>
                ) : null}
                {canArchive ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-archive-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => setConfirm({ kind: 'archive', doc })}
                  >
                    Arşivle
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
              <strong>Belge bilgileri</strong>
              <Button type="button" size="sm" variant="secondary" onClick={() => setEditing(null)}>
                İptal
              </Button>
            </header>
            <Input label="Ad" value={editTitle} onChange={(event) => setEditTitle(event.target.value)} />
            <Select label="Tür" value={editType} onChange={(event) => setEditType(event.target.value as DocumentType)}>
              {DOCUMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </Select>
            <Input label="Kategori" value={editCategory} onChange={(event) => setEditCategory(event.target.value)} />
            <TextArea
              label="Açıklama"
              value={editDescription}
              onChange={(event) => setEditDescription(event.target.value)}
            />
            <Button type="button" size="sm" disabled={busyId === editing.id} onClick={() => void saveMeta()}>
              Kaydet
            </Button>
          </div>
        </div>
      ) : null}
      {confirm ? (
        <div className="crm-doc-gallery__modal" role="alertdialog" data-testid="crm-doc-confirm-modal">
          <div className="crm-doc-gallery__modal-panel">
            <header>
              <strong>{confirm.kind === 'archive' ? 'Belgeyi arşivle?' : 'Belgeyi bu kayıttan kaldır?'}</strong>
            </header>
            <p>
              {confirm.kind === 'archive'
                ? 'Bu işlem belgeyi yumuşak siler. Başka kayıtlara bağlıysa orada da görünmez.'
                : 'Belge depodan silinmez. Yalnızca bu kişi/anlaşma bağlantısı kaldırılır.'}
            </p>
            <div className="crm-doc-gallery__actions">
              <Button type="button" size="sm" variant="secondary" onClick={() => setConfirm(null)}>
                Vazgeç
              </Button>
              <Button type="button" size="sm" data-testid="crm-doc-confirm" onClick={() => void applyConfirm()}>
                Onayla
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
