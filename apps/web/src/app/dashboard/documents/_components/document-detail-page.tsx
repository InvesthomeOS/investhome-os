'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  askDrawing,
  drawingPreviewUrl,
  fetchDrawingAnalysis,
  fetchDrawingProcessingStatus,
  reprocessDrawing,
  type DrawingAnalysis,
} from '@/lib/api/drawing-intelligence';
import {
  acceptClassification,
  askDocument,
  exportDocumentAnalysis,
  fetchDocumentAnalysis,
  fetchProcessingStatus,
  reprocessDocument,
  rejectClassification,
  type AskDocumentResponse,
  type DocumentAnalysis,
} from '@/lib/api/document-intelligence';
import {
  archiveDocument,
  DOCUMENT_LINK_ENTITY_TYPES,
  documentDownloadUrl,
  documentPreviewUrl,
  fetchDocument,
  fetchDocumentVersions,
  formatDocumentDate,
  formatFileSize,
  linkDocument,
  restoreDocument,
  restoreDocumentVersion,
  unlinkDocument,
  type Document,
  type DocumentVersion,
} from '@/lib/api/documents';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useDocumentLabels } from '@/lib/i18n/document-labels';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';

type TabId =
  | 'overview'
  | 'preview'
  | 'drawing'
  | 'summary'
  | 'extracted'
  | 'risks'
  | 'ask'
  | 'versions'
  | 'related'
  | 'activity';

const BASE_TABS: TabId[] = [
  'overview',
  'preview',
  'summary',
  'extracted',
  'risks',
  'ask',
  'versions',
  'related',
  'activity',
];

const DRAWING_TYPES = new Set(['architectural_drawing', 'construction_drawing']);

interface DocumentDetailPageProps {
  documentId: string;
}

export function DocumentDetailPage({ documentId }: DocumentDetailPageProps) {
  const t = useTranslations('documents');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const { user } = useAuth();
  const {
    getTypeLabel,
    getFileKindLabel,
    getFolderLabel,
    getVisibilityLabel,
    getStatusLabel,
    getConfidentialityLabel,
  } = useDocumentLabels();

  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [drawingAnalysis, setDrawingAnalysis] = useState<DrawingAnalysis | null>(null);
  const [drawingStatus, setDrawingStatus] = useState<string | null>(null);
  const [drawingQuestion, setDrawingQuestion] = useState('');
  const [drawingAnswer, setDrawingAnswer] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [askResult, setAskResult] = useState<AskDocumentResponse | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [actionPending, setActionPending] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [linkEntityType, setLinkEntityType] = useState<string>('project');
  const [linkEntityId, setLinkEntityId] = useState('');

  const canArchive = user ? hasPermission(user, 'documents', 'archive') : false;
  const canDownload = user ? hasPermission(user, 'documents', 'download') : false;
  const canUpdate = user ? hasPermission(user, 'documents', 'update') : false;
  const canView = user ? hasPermission(user, 'documents', 'view') : false;

  const loadIntelligence = useCallback(async (docId: string, docType: string) => {
    setLoadingAnalysis(true);
    try {
      const [statusPayload, analysisPayload] = await Promise.all([
        fetchProcessingStatus(docId),
        fetchDocumentAnalysis(docId).catch(() => null),
      ]);
      setProcessingStatus(statusPayload.processing_status);
      setAnalysis(analysisPayload);
      if (DRAWING_TYPES.has(docType)) {
        const [drawingStatusPayload, drawingPayload] = await Promise.all([
          fetchDrawingProcessingStatus(docId).catch(() => null),
          fetchDrawingAnalysis(docId).catch(() => null),
        ]);
        setDrawingStatus(drawingStatusPayload?.processing_status ?? null);
        setDrawingAnalysis(drawingPayload);
      } else {
        setDrawingStatus(null);
        setDrawingAnalysis(null);
      }
    } catch {
      setAnalysis(null);
      setDrawingAnalysis(null);
    } finally {
      setLoadingAnalysis(false);
    }
  }, []);

  const loadDocument = useCallback(async () => {
    if (!canView) {
      setError('permission_denied');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const doc = await fetchDocument(documentId);
      setDocument(doc);
      const versionPayload = await fetchDocumentVersions(doc.id).catch(() => ({ items: [] as DocumentVersion[] }));
      setVersions(versionPayload.items);
      await loadIntelligence(doc.id, doc.document_type);
    } catch {
      setError(t('loadError'));
      setDocument(null);
    } finally {
      setLoading(false);
    }
  }, [canView, documentId, loadIntelligence, t]);

  useEffect(() => {
    void loadDocument();
  }, [loadDocument]);

  useEffect(() => {
    if (!document || !processingStatus) return;
    if (['queued', 'processing', 'extracting_text', 'running_ocr', 'classifying', 'analyzing'].includes(processingStatus)) {
      const timer = window.setInterval(() => {
        void fetchProcessingStatus(document.id)
          .then((payload) => {
            setProcessingStatus(payload.processing_status);
            if (payload.processing_status === 'completed') {
              void fetchDocumentAnalysis(document.id).then(setAnalysis).catch(() => undefined);
            }
          })
          .catch(() => undefined);
      }, 3000);
      return () => window.clearInterval(timer);
    }
    return undefined;
  }, [document, processingStatus]);

  const isDrawing = document ? DRAWING_TYPES.has(document.document_type) : false;
  const tabs: TabId[] = isDrawing
    ? ['overview', 'preview', 'drawing', ...BASE_TABS.filter((tab) => tab !== 'overview' && tab !== 'preview')]
    : BASE_TABS;

  if (!canView || error === 'permission_denied') {
    return (
      <div className="leads-page">
        <header className="leads-page__header">
          <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
          <h1>{t('title')}</h1>
        </header>
        <div className="documents-empty">
          <h2>{t('permissionDenied')}</h2>
          <p>{t('permissionDeniedHint')}</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return <p className="leads-page__loading">{tCommon('loading')}</p>;
  }

  if (error || !document) {
    return (
      <div className="leads-page">
        <div className="leads-page__error">
          <p>{error ?? t('loadError')}</p>
          <Link href="/dashboard/knowledge/documents" className="leads__button leads__button--secondary">
            {t('detailBack')}
          </Link>
        </div>
      </div>
    );
  }

  const summaryText = locale === 'en' ? analysis?.ai_summary_en ?? analysis?.ai_summary : analysis?.ai_summary;

  const handleArchive = async () => {
    setArchiving(true);
    setActionError(null);
    try {
      if (document.archived_at) {
        await restoreDocument(document.id);
      } else {
        await archiveDocument(document.id);
      }
      router.push('/dashboard/knowledge/documents');
    } catch {
      setActionError(t('actionError'));
    } finally {
      setArchiving(false);
    }
  };

  const handleRestoreVersion = async (versionId: string) => {
    setActionPending(true);
    setActionError(null);
    try {
      const restored = await restoreDocumentVersion(document.id, versionId);
      router.replace(`/dashboard/documents/${restored.id}`);
    } catch {
      setActionError(t('actionError'));
    } finally {
      setActionPending(false);
    }
  };

  const handleLink = async () => {
    if (!linkEntityId.trim()) return;
    setActionPending(true);
    setActionError(null);
    try {
      await linkDocument(document.id, linkEntityType, linkEntityId.trim());
      setLinkEntityId('');
      await loadDocument();
    } catch {
      setActionError(t('actionError'));
    } finally {
      setActionPending(false);
    }
  };

  const handleUnlink = async (linkId: string) => {
    setActionPending(true);
    setActionError(null);
    try {
      await unlinkDocument(document.id, linkId);
      await loadDocument();
    } catch {
      setActionError(t('actionError'));
    } finally {
      setActionPending(false);
    }
  };

  return (
    <div className="leads-page documents-detail-page">
      <header className="leads-page__header documents-detail-page__header">
        <div>
          <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
          <h1>{document.title}</h1>
          <p className="leads-page__subtitle">
            {document.original_file_name} · {formatFileSize(document.file_size)} · v{document.version_number}
          </p>
          {processingStatus && (
            <span className="documents-processing-badge">
              {t(`intelligence.processing.${processingStatus}` as never)}
            </span>
          )}
        </div>
        <div className="leads-page__actions">
          <Link href="/dashboard/knowledge/documents" className="leads__button leads__button--ghost">
            {t('detailBack')}
          </Link>
          {canDownload && (
            <a className="leads__button leads__button--secondary" href={documentDownloadUrl(document.id)} target="_blank" rel="noreferrer">
              {t('download')}
            </a>
          )}
          {canArchive && (
            <button type="button" className="leads__button leads__button--danger" disabled={archiving} onClick={() => void handleArchive()}>
              {document.archived_at ? t('restore') : t('archive')}
            </button>
          )}
        </div>
      </header>

      {actionError && <p className="leads-page__error">{actionError}</p>}

      <nav className="documents-tabs" aria-label={t('intelligence.tabsLabel')}>
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? 'documents-tabs__tab documents-tabs__tab--active' : 'documents-tabs__tab'}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'drawing' ? t('intelligence.drawing.tab') : t(`intelligence.tabs.${tab}` as never)}
          </button>
        ))}
      </nav>

      <div className="documents-detail-page__panel">
        {activeTab === 'overview' && (
          <dl className="leads-drawer__grid">
            <div><dt>{t('columns.type')}</dt><dd>{getTypeLabel(document.document_type)}</dd></div>
            <div><dt>{t('columns.fileKind')}</dt><dd>{getFileKindLabel(document.file_kind)}</dd></div>
            <div><dt>{t('columns.folder')}</dt><dd>{getFolderLabel(document.folder)}</dd></div>
            <div><dt>{t('columns.visibility')}</dt><dd>{getVisibilityLabel(document.visibility)}</dd></div>
            <div><dt>{t('columns.status')}</dt><dd>{getStatusLabel(document.status)}</dd></div>
            <div><dt>{t('columns.confidentiality')}</dt><dd>{getConfidentialityLabel(document.confidentiality_level)}</dd></div>
            <div><dt>{t('columns.version')}</dt><dd>v{document.version_number}</dd></div>
            <div><dt>{t('columns.fileSize')}</dt><dd>{formatFileSize(document.file_size)}</dd></div>
            <div><dt>{t('columns.relatedRecord')}</dt><dd>{document.related_record_label ?? tCommon('noValue')}</dd></div>
            <div><dt>{t('columns.owner')}</dt><dd>{document.owner_name ?? document.uploaded_by_name ?? tCommon('noValue')}</dd></div>
            <div><dt>{t('columns.uploadedBy')}</dt><dd>{document.uploaded_by_name ?? tCommon('noValue')}</dd></div>
            <div><dt>{t('createdLabel')}</dt><dd>{formatDocumentDate(document.created_at, locale)}</dd></div>
            <div><dt>{t('modifiedLabel')}</dt><dd>{formatDocumentDate(document.updated_at, locale)}</dd></div>
            <div><dt>{t('columns.tags')}</dt><dd>{document.tags ?? tCommon('noValue')}</dd></div>
            <div className="leads-form__full"><dt>{t('columns.description')}</dt><dd>{document.description ?? tCommon('noValue')}</dd></div>
            <div className="leads-form__full"><dt>{t('columns.notes')}</dt><dd>{document.notes ?? tCommon('noValue')}</dd></div>
          </dl>
        )}

        {activeTab === 'preview' && (
          document.is_previewable && canDownload ? (
            <div className="documents-preview documents-preview--full">
              {['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(document.file_extension.toLowerCase()) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={documentPreviewUrl(document.id)}
                  alt={document.title}
                  className="documents-preview__image"
                />
              ) : (
                <iframe title={document.title} src={documentPreviewUrl(document.id)} className="documents-preview__frame documents-preview__frame--tall" />
              )}
            </div>
          ) : (
            <div className="documents-preview documents-preview--unavailable">
              <span className="documents-grid__ext" aria-label={t('fileIconLabel')}>
                {document.file_extension.toUpperCase()}
              </span>
              <p>{t('previewUnavailable')}</p>
              <p>{t('previewDownloadHint')}</p>
              <p>{document.original_file_name} · {formatFileSize(document.file_size)}</p>
              {canDownload && (
                <a className="leads__button leads__button--secondary" href={documentDownloadUrl(document.id)} target="_blank" rel="noreferrer">
                  {t('download')}
                </a>
              )}
            </div>
          )
        )}

        {activeTab === 'drawing' && isDrawing && (
          <section className="documents-intelligence-section">
            {loadingAnalysis && <p>{t('intelligence.drawing.loading')}</p>}
            {drawingStatus && (
              <span className="documents-processing-badge">
                {t.has(`intelligence.drawing.processing.${drawingStatus}` as never)
                  ? t(`intelligence.drawing.processing.${drawingStatus}` as never)
                  : drawingStatus}
              </span>
            )}
            {drawingAnalysis?.preview_status === 'ready' && canDownload ? (
              <div className="documents-preview">
                <iframe title={document.title} src={drawingPreviewUrl(document.id)} className="documents-preview__frame documents-preview__frame--tall" />
              </div>
            ) : (
              <p>{t('intelligence.drawing.previewUnavailable')}</p>
            )}
            {drawingAnalysis && (
              <dl className="leads-drawer__grid">
                <div><dt>{t('intelligence.drawing.discipline')}</dt><dd>{drawingAnalysis.discipline ?? tCommon('noValue')}</dd></div>
                <div><dt>{t('intelligence.drawing.drawingType')}</dt><dd>{drawingAnalysis.drawing_type ?? tCommon('noValue')}</dd></div>
                <div>
                  <dt>{t('intelligence.drawing.scale')}</dt>
                  <dd>
                    {drawingAnalysis.scale_corrected ?? drawingAnalysis.scale_detected ?? tCommon('noValue')}
                    {drawingAnalysis.scale_confidence === 'low' && ` (${t('intelligence.drawing.scaleLowConfidence')})`}
                  </dd>
                </div>
              </dl>
            )}
            <div className="documents-ask">
              <textarea
                value={drawingQuestion}
                onChange={(e) => setDrawingQuestion(e.target.value)}
                placeholder={t('intelligence.drawing.askPlaceholder')}
              />
              <button
                type="button"
                className="leads__button"
                disabled={actionPending || !drawingQuestion.trim()}
                onClick={async () => {
                  setActionPending(true);
                  try {
                    const response = await askDrawing(document.id, drawingQuestion.trim(), locale === 'en' ? 'en' : 'tr');
                    setDrawingAnswer(response.answer);
                  } finally {
                    setActionPending(false);
                  }
                }}
              >
                {t('intelligence.askSubmit')}
              </button>
              {drawingAnswer && <p>{drawingAnswer}</p>}
            </div>
            <button
              type="button"
              className="leads__button leads__button--ghost"
              disabled={actionPending}
              onClick={async () => {
                setActionPending(true);
                try {
                  await reprocessDrawing(document.id);
                  await loadIntelligence(document.id, document.document_type);
                } finally {
                  setActionPending(false);
                }
              }}
            >
              {t('intelligence.drawing.reprocess')}
            </button>
          </section>
        )}

        {activeTab === 'summary' && (
          <section className="documents-intelligence-section">
            {loadingAnalysis && <p>{t('intelligence.loading')}</p>}
            {!loadingAnalysis && !summaryText && <p>{t('intelligence.emptySummary')}</p>}
            {summaryText && (
              <>
                <p className="documents-disclaimer">{t('intelligence.disclaimer')}</p>
                <p>{summaryText}</p>
              </>
            )}
          </section>
        )}

        {activeTab === 'extracted' && (
          <section className="documents-intelligence-section">
            {analysis?.extracted_parties?.length ? (
              <div>
                <h3>{t('intelligence.fields.parties')}</h3>
                <ul>{analysis.extracted_parties.map((party) => <li key={party}>{party}</li>)}</ul>
              </div>
            ) : null}
            {!analysis?.extracted_parties?.length && !analysis?.extracted_dates?.length && (
              <p>{t('intelligence.emptyExtracted')}</p>
            )}
          </section>
        )}

        {activeTab === 'risks' && (
          <section className="documents-intelligence-section">
            {analysis?.extracted_risks?.length ? (
              <table className="documents-risk-table">
                <thead>
                  <tr>
                    <th>{t('intelligence.risk.severity')}</th>
                    <th>{t('intelligence.risk.category')}</th>
                    <th>{t('intelligence.risk.description')}</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.extracted_risks.map((risk, index) => (
                    <tr key={`risk-${index}`}>
                      <td>{t(`intelligence.severity.${risk.severity}` as never)}</td>
                      <td>{t(`intelligence.riskCategories.${risk.category}` as never)}</td>
                      <td>{risk.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>{t('intelligence.emptyRisks')}</p>
            )}
          </section>
        )}

        {activeTab === 'ask' && (
          <section className="documents-intelligence-section">
            <p className="documents-disclaimer">{t('intelligence.disclaimer')}</p>
            <textarea
              className="documents-ask-input"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={t('intelligence.askPlaceholder')}
              rows={3}
            />
            <button
              type="button"
              className="leads__button leads__button--primary"
              disabled={actionPending}
              onClick={async () => {
                if (!question.trim()) return;
                setActionPending(true);
                try {
                  const response = await askDocument(document.id, question.trim(), locale === 'en' ? 'en' : 'tr');
                  setAskResult(response);
                } finally {
                  setActionPending(false);
                }
              }}
            >
              {t('intelligence.askSubmit')}
            </button>
            {askResult && <div className="documents-ask-result"><p>{askResult.answer}</p></div>}
          </section>
        )}

        {activeTab === 'versions' && (
          <section className="documents-versions">
            <h2>{t('versionHistory')}</h2>
            {versions.length === 0 ? <p>{t('noVersions')}</p> : (
              <ul className="documents-versions__list">
                {versions.map((version) => (
                  <li key={version.id} className="documents-versions__item">
                    <div>
                      <strong>v{version.version_number}</strong>
                      {version.is_latest_version && (
                        <span className="documents-processing-badge">{t('currentVersion')}</span>
                      )}
                      <span> — {version.original_file_name}</span>
                      <span className="documents-table__filename">
                        {formatDocumentDate(version.created_at, locale)}
                        {version.uploaded_by_name ? ` · ${version.uploaded_by_name}` : ''}
                        {version.version_notes ? ` · ${version.version_notes}` : ''}
                      </span>
                    </div>
                    {canUpdate && !version.is_latest_version && document.is_latest_version && (
                      <button
                        type="button"
                        className="leads__button leads__button--secondary"
                        disabled={actionPending}
                        onClick={() => void handleRestoreVersion(version.id)}
                      >
                        {actionPending ? t('restoringVersion') : t('restoreVersion')}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {activeTab === 'related' && (
          <section className="documents-related">
            <h2>{t('relatedRecords')}</h2>
            {document.links.length === 0 ? (
              <p>{t('relationEmpty')}</p>
            ) : (
              <ul className="documents-related__list">
                {document.links.map((link) => (
                  <li key={link.id} className="documents-related__item">
                    <span>
                      {t.has(`relatedModules.${link.entity_type}` as never)
                        ? t(`relatedModules.${link.entity_type}` as never)
                        : link.entity_type}
                      : {link.entity_id}
                    </span>
                    {canUpdate && (
                      <button
                        type="button"
                        className="leads__button leads__button--ghost"
                        disabled={actionPending}
                        onClick={() => void handleUnlink(link.id)}
                      >
                        {t('relationUnlink')}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {canUpdate && (
              <div className="documents-related__form">
                <h3>{t('addRelation')}</h3>
                <label>
                  <span>{t('relationEntityType')}</span>
                  <select value={linkEntityType} onChange={(e) => setLinkEntityType(e.target.value)}>
                    {DOCUMENT_LINK_ENTITY_TYPES.map((entityType) => (
                      <option key={entityType} value={entityType}>
                        {t.has(`relatedModules.${entityType}` as never)
                          ? t(`relatedModules.${entityType}` as never)
                          : entityType}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>{t('relationEntityId')}</span>
                  <input
                    type="text"
                    value={linkEntityId}
                    onChange={(e) => setLinkEntityId(e.target.value)}
                    placeholder="uuid"
                  />
                </label>
                <button
                  type="button"
                  className="leads__button leads__button--primary"
                  disabled={actionPending || !linkEntityId.trim()}
                  onClick={() => void handleLink()}
                >
                  {t('relationSubmit')}
                </button>
              </div>
            )}
          </section>
        )}

        {activeTab === 'activity' && (
          <EntityActivityTimeline entityType="document" entityId={document.id} title={t('activityTitle')} />
        )}
      </div>

      <footer className="documents-detail-page__footer">
        <button
          type="button"
          className="leads__button leads__button--ghost"
          disabled={actionPending}
          onClick={async () => {
            setActionPending(true);
            try {
              const payload = await reprocessDocument(document.id);
              setProcessingStatus(payload.processing_status);
            } finally {
              setActionPending(false);
            }
          }}
        >
          {t('intelligence.reprocess')}
        </button>
        {analysis?.classification_status === 'pending' && analysis.detected_document_type && (
          <>
            <button type="button" className="leads__button leads__button--secondary" disabled={actionPending} onClick={() => void acceptClassification(document.id).then(setAnalysis)}>
              {t('intelligence.acceptClassification')}
            </button>
            <button type="button" className="leads__button leads__button--ghost" disabled={actionPending} onClick={() => void rejectClassification(document.id).then(setAnalysis)}>
              {t('intelligence.rejectClassification')}
            </button>
          </>
        )}
        <button type="button" className="leads__button leads__button--ghost" onClick={() => void exportDocumentAnalysis(document.id)}>
          {t('intelligence.export')}
        </button>
      </footer>
    </div>
  );
}
