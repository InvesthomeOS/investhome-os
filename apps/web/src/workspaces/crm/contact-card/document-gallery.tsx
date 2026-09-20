'use client';

import { useEffect, useMemo, useState } from 'react';

import { Button } from '@investhome/ui';

import { documentDownloadUrl, documentPreviewUrl } from '@/lib/api/documents';
import { setCrmDocumentVisibility } from '@/workspaces/crm/api/contacts';

export type GalleryDocument = {
  id: string;
  title: string;
  original_file_name?: string | null;
  document_type?: string | null;
  mime_type?: string | null;
  source?: string | null;
  checksum?: string | null;
  bitrix_file_id?: string | null;
  hidden_from_view?: boolean;
  created_at?: string | null;
  file_kind?: string | null;
  file_extension?: string | null;
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
    const keys = [
      item.bitrix_file_id ? `bx:${item.bitrix_file_id}` : '',
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

function PreviewBody({ doc }: { doc: GalleryDocument }) {
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

export function DocumentGallery({
  documents,
  entityType,
  entityId,
  onChanged,
}: {
  documents: GalleryDocument[];
  entityType: string;
  entityId: string;
  onChanged: () => void;
}) {
  const [showHidden, setShowHidden] = useState(false);
  const [preview, setPreview] = useState<GalleryDocument | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const unique = useMemo(() => dedupeGalleryDocuments(documents), [documents]);
  const visible = unique.filter((item) => showHidden || !item.hidden_from_view);
  const hiddenCount = unique.filter((item) => item.hidden_from_view).length;

  const toggleHidden = async (doc: GalleryDocument, hidden: boolean) => {
    setBusyId(doc.id);
    try {
      await setCrmDocumentVisibility({
        document_id: doc.id,
        entity_type: entityType,
        entity_id: entityId,
        hidden,
      });
      onChanged();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="crm-doc-gallery" data-testid="crm-document-gallery">
      <div className="crm-doc-gallery__tools">
        <Button type="button" size="sm" variant="secondary" onClick={() => setShowHidden((value) => !value)}>
          {showHidden ? 'Gizlenenleri Gizle' : 'Gizlenenleri Göster'}
          {hiddenCount ? ` (${hiddenCount})` : ''}
        </Button>
      </div>
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
                {doc.hidden_from_view ? (
                  <button
                    type="button"
                    data-testid={`crm-doc-restore-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => toggleHidden(doc, false)}
                  >
                    Geri Getir
                  </button>
                ) : (
                  <button
                    type="button"
                    data-testid={`crm-doc-hide-${doc.id}`}
                    disabled={busyId === doc.id}
                    onClick={() => toggleHidden(doc, true)}
                  >
                    Görünümden Kaldır
                  </button>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
      {preview ? (
        <div className="crm-doc-gallery__modal" data-testid="crm-doc-preview-modal" role="dialog">
          <div className="crm-doc-gallery__modal-panel">
            <header>
              <strong>{preview.original_file_name || preview.title}</strong>
              <Button type="button" size="sm" variant="secondary" onClick={() => setPreview(null)}>
                Kapat
              </Button>
            </header>
            <PreviewBody doc={preview} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
