'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import {
  createShareLink,
  formatFileSize,
  getDownloadUrl,
  getPreviewUrl,
  type CompanyDocument,
} from '@/lib/api/company-documents';

type Tab = 'preview' | 'general' | 'file' | 'versions' | 'permissions' | 'approval' | 'signature' | 'expiration' | 'activity';

type Props = {
  document: CompanyDocument;
  open: boolean;
  onClose: () => void;
  canDownload: boolean;
  canArchive: boolean;
  onAction: (type: string) => void;
};

const PREVIEWABLE = new Set(['pdf', 'jpg', 'jpeg', 'png', 'webp', 'txt']);

export function CompanyDocumentDetailDrawer({ document, open, onClose, canDownload, canArchive, onAction }: Props) {
  const t = useTranslations('company.documents.detail');
  const [tab, setTab] = useState<Tab>('preview');
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  if (!open) return null;

  const ext = document.file_extension?.toLowerCase() ?? '';
  const canPreview = PREVIEWABLE.has(ext);

  const handleShare = async () => {
    const link = await createShareLink(document.id, { expires_in_hours: 72, max_downloads: 10 });
    setShareUrl(link.secure_url ?? link.token);
  };

  const tabs: Tab[] = ['preview', 'general', 'file', 'versions', 'permissions', 'approval', 'signature', 'expiration', 'activity'];

  return (
    <div className="company-doc-drawer-overlay" role="dialog" aria-modal="true">
      <div className="company-doc-drawer">
        <header className="company-doc-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{document.document_number}</p>
            <h2>{document.title}</h2>
            <StatusLine status={document.status} />
          </div>
          <div className="company-doc-drawer__actions">
            {canDownload && (
              <a href={getDownloadUrl(document.id)} download>{t('download')}</a>
            )}
            <Button variant="secondary" onClick={() => onAction(document.is_favorited ? 'unfavorite' : 'favorite')}>
              {document.is_favorited ? t('unfavorite') : t('favorite')}
            </Button>
            <Button variant="secondary" onClick={() => void handleShare()}>{t('share')}</Button>
            {canArchive && (
              <>
                <Button variant="secondary" onClick={() => onAction('archive')}>{t('archive')}</Button>
                <Button variant="secondary" onClick={() => onAction('trash')}>{t('trash')}</Button>
              </>
            )}
            <button type="button" onClick={onClose} aria-label={t('close')}>×</button>
          </div>
        </header>

        <nav className="company-doc-drawer__tabs">
          {tabs.map((key) => (
            <button key={key} type="button" className={tab === key ? 'is-active' : ''} onClick={() => setTab(key)}>
              {t(`tabs.${key}`)}
            </button>
          ))}
        </nav>

        <div className="company-doc-drawer__body">
          {tab === 'preview' && (
            canPreview ? (
              ext === 'txt' ? (
                <iframe title={t('preview')} src={getPreviewUrl(document.id)} className="company-doc-preview-frame" />
              ) : (
                <object data={getPreviewUrl(document.id)} type={document.mime_type ?? 'application/pdf'} className="company-doc-preview-frame">
                  <p>{t('previewFallback')}</p>
                </object>
              )
            ) : (
              <p>{t('previewUnavailable', { ext: ext || 'unknown' })}</p>
            )
          )}

          {tab === 'general' && (
            <dl className="company-doc-detail-grid">
              <div><dt>{t('fields.title')}</dt><dd>{document.title}</dd></div>
              <div><dt>{t('fields.category')}</dt><dd>{document.category}</dd></div>
              <div><dt>{t('fields.confidentiality')}</dt><dd>{document.confidentiality_level}</dd></div>
              <div><dt>{t('fields.owner')}</dt><dd>{document.owner_name ?? '—'}</dd></div>
              <div><dt>{t('fields.folder')}</dt><dd>{document.folder_name ?? '—'}</dd></div>
              <div><dt>{t('fields.description')}</dt><dd>{document.description ?? '—'}</dd></div>
              <div><dt>{t('fields.tags')}</dt><dd>{document.tags.join(', ') || '—'}</dd></div>
            </dl>
          )}

          {tab === 'file' && (
            <dl className="company-doc-detail-grid">
              <div><dt>{t('fields.fileName')}</dt><dd>{document.file_name}</dd></div>
              <div><dt>{t('fields.size')}</dt><dd>{formatFileSize(document.file_size)}</dd></div>
              <div><dt>{t('fields.mime')}</dt><dd>{document.mime_type}</dd></div>
              <div><dt>{t('fields.checksum')}</dt><dd><code>{document.checksum}</code></dd></div>
              <div><dt>{t('fields.version')}</dt><dd>{document.current_version_number}</dd></div>
            </dl>
          )}

          {tab === 'versions' && (
            <ul className="company-doc-versions">
              {(document.versions ?? []).map((v) => (
                <li key={v.id}>
                  <strong>v{v.version_number}</strong> — {v.original_file_name} ({formatFileSize(v.file_size)})
                  {v.is_current && ` · ${t('currentVersion')}`}
                  {v.version_notes && <p>{v.version_notes}</p>}
                </li>
              ))}
            </ul>
          )}

          {tab === 'permissions' && (
            <p>{t('permissionsStub')}</p>
          )}

          {tab === 'approval' && (
            <p>{document.status === 'pending_approval' ? t('approvalPending') : t('approvalNone')}</p>
          )}

          {tab === 'signature' && (
            <p>{t('signatureStub')}</p>
          )}

          {tab === 'expiration' && (
            <dl className="company-doc-detail-grid">
              <div><dt>{t('fields.effective')}</dt><dd>{document.effective_date ?? '—'}</dd></div>
              <div><dt>{t('fields.expiration')}</dt><dd>{document.expiration_date ?? '—'}</dd></div>
              <div><dt>{t('fields.renewal')}</dt><dd>{document.renewal_date ?? '—'}</dd></div>
              {document.has_legal_hold && <div><dt>{t('fields.legalHold')}</dt><dd>{t('legalHoldActive')}</dd></div>}
            </dl>
          )}

          {tab === 'activity' && (
            <p>{t('activityHint')}</p>
          )}
        </div>

        {shareUrl && (
          <div className="company-doc-share-banner">
            <span>{t('shareCreated')}</span>
            <code>{shareUrl}</code>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusLine({ status }: { status: string }) {
  return <span className="company-doc-status">{status}</span>;
}
