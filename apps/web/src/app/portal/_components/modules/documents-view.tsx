'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import type { DocumentCategory } from '../../_data/types';
import { formatDate } from '../../_lib/format';
import { getDocumentsFor } from '../../_lib/permissions';
import { usePortalSession } from '../../_state/portal-session';
import { PageHeader } from '../page-header';

const CATEGORIES: Array<DocumentCategory | 'all'> = [
  'all',
  'contracts',
  'statements',
  'kyc',
  'project',
  'tax',
  'legal',
  'other',
];

export function DocumentsView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>('all');
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const docs = useMemo(() => {
    if (!investorId) return [];
    const all = getDocumentsFor(investorId);
    if (category === 'all') return all;
    return all.filter((d) => d.category === category);
  }, [investorId, category]);

  if (!investorId) return null;

  const preview = docs.find((d) => d.id === previewId) ?? null;

  async function download(docId: string) {
    setError(null);
    const res = await fetch(`/api/portal/documents/${docId}/download`, {
      credentials: 'include',
    });
    if (!res.ok) {
      setError(t('documents.forbidden'));
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${docId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="portal-page" data-testid="portal-documents">
      <PageHeader title={t('documents.title')} subtitle={t('documents.subtitle')} />
      <div className="portal-tabs" role="tablist">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            type="button"
            role="tab"
            aria-selected={category === c}
            onClick={() => setCategory(c)}
            data-testid={`portal-doc-cat-${c}`}
          >
            {c === 'all' ? t('documents.all') : c}
          </button>
        ))}
      </div>
      {error ? <p className="portal-login__error">{error}</p> : null}
      <div className="portal-grid-2">
        <section className="portal-panel">
          <table className="portal-table">
            <thead>
              <tr>
                <th />
                <th>{t('documents.category')}</th>
                <th>{t('documents.version')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} data-testid={`portal-doc-${d.id}`}>
                  <td>
                    <strong>{d.title}</strong>
                    <div className="portal-list__meta">
                      {d.projectName ?? '—'} · {formatDate(d.uploadedAt, locale)} · {d.sizeLabel}
                    </div>
                  </td>
                  <td>{d.category}</td>
                  <td>{d.version}</td>
                  <td>
                    <div className="portal-actions">
                      <button
                        type="button"
                        className="portal-btn"
                        disabled={!d.canPreview}
                        onClick={() => setPreviewId(d.id)}
                      >
                        {t('documents.preview')}
                      </button>
                      <button
                        type="button"
                        className="portal-btn portal-btn--primary"
                        disabled={!d.canDownload}
                        onClick={() => void download(d.id)}
                        data-testid={`portal-doc-dl-${d.id}`}
                      >
                        {t('documents.download')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="portal-panel" data-testid="portal-doc-preview">
          <h2 className="portal-panel__title">{t('documents.preview')}</h2>
          {preview ? (
            <div>
              <p>
                <strong>{preview.title}</strong>
              </p>
              <p className="portal-list__meta">
                {preview.version} · {preview.mime} · {preview.category}
              </p>
              <div className="portal-gap" style={{ marginTop: '0.75rem' }}>
                Preview pane (permission-scoped). Download uses `/api/portal/documents/{'{id}'}/download`.
              </div>
            </div>
          ) : (
            <div className="portal-empty">—</div>
          )}
        </section>
      </div>
    </div>
  );
}
