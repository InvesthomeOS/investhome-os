'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  addDrawingAnnotation,
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
  documentDownloadUrl,
  documentPreviewUrl,
  fetchDocumentVersions,
  formatDocumentDate,
  formatFileSize,
  type Document,
  type DocumentVersion,
} from '@/lib/api/documents';
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

  useEffect(() => {
    if (!document) {
      setVersions([]);
      setAnalysis(null);
      setAskResult(null);
      setActiveTab('overview');
      return;
    }
    void fetchDocumentVersions(document.id)
      .then((response) => setVersions(response.items))
      .catch(() => setVersions([]));
    void loadIntelligence(document.id, document.document_type);
  }, [document, loadIntelligence]);

  const isDrawing = document ? DRAWING_TYPES.has(document.document_type) : false;
  const tabs: TabId[] = isDrawing
    ? ['overview', 'preview', 'drawing', ...BASE_TABS.filter((tab) => tab !== 'overview' && tab !== 'preview')]
    : BASE_TABS;

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

  if (!document) return null;

  const summaryText = locale === 'en' ? analysis?.ai_summary_en ?? analysis?.ai_summary : analysis?.ai_summary;

  const handleReprocess = async () => {
    setActionPending(true);
    try {
      const payload = await reprocessDocument(document.id);
      setProcessingStatus(payload.processing_status);
    } finally {
      setActionPending(false);
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) return;
    setActionPending(true);
    try {
      const response = await askDocument(document.id, question.trim(), locale === 'en' ? 'en' : 'tr');
      setAskResult(response);
    } finally {
      setActionPending(false);
    }
  };

  return (
    <div className="leads-drawer" role="presentation" onClick={onClose}>
      <aside className="leads-drawer__panel documents-drawer documents-drawer--tabs" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="leads-drawer__header">
          <div>
            <p className="dashboard__eyebrow">{t('detailEyebrow')}</p>
            <h2>{document.title}</h2>
            {processingStatus && (
              <span className="documents-processing-badge">
                {t(`intelligence.processing.${processingStatus}` as never)}
              </span>
            )}
          </div>
          <button type="button" className="leads__button leads__button--ghost" onClick={onClose}>{tCommon('close')}</button>
        </header>

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

        <div className="documents-tab-panel">
          {activeTab === 'overview' && (
            <dl className="leads-drawer__grid">
              <div><dt>{t('columns.type')}</dt><dd>{getTypeLabel(document.document_type)}</dd></div>
              <div><dt>{t('intelligence.userType')}</dt><dd>{getTypeLabel(document.document_type)}</dd></div>
              <div><dt>{t('intelligence.aiDetectedType')}</dt><dd>{analysis?.detected_document_type ? getTypeLabel(analysis.detected_document_type as never) : tCommon('noValue')}</dd></div>
              <div><dt>{t('columns.status')}</dt><dd>{getStatusLabel(document.status)}</dd></div>
              <div><dt>{t('columns.confidentiality')}</dt><dd>{getConfidentialityLabel(document.confidentiality_level)}</dd></div>
              <div><dt>{t('columns.version')}</dt><dd>v{document.version_number}</dd></div>
              <div><dt>{t('columns.relatedRecord')}</dt><dd>{document.related_record_label ?? tCommon('noValue')}</dd></div>
              <div><dt>{t('columns.uploadedBy')}</dt><dd>{document.uploaded_by_name ?? tCommon('noValue')}</dd></div>
              <div><dt>{t('columns.documentDate')}</dt><dd>{formatDocumentDate(document.document_date, locale)}</dd></div>
              <div><dt>{t('columns.updatedDate')}</dt><dd>{formatDocumentDate(document.updated_at, locale)}</dd></div>
            </dl>
          )}

          {activeTab === 'preview' && (
            document.is_previewable && canDownload ? (
              <div className="documents-preview">
                <iframe title={document.title} src={documentPreviewUrl(document.id)} className="documents-preview__frame" />
              </div>
            ) : (
              <div className="documents-preview documents-preview--unavailable">
                <p>{t('previewUnavailable')}</p>
                <p>{document.original_file_name} · {formatFileSize(document.file_size, locale)}</p>
              </div>
            )
          )}

          {activeTab === 'drawing' && isDrawing && (
            <section className="documents-intelligence-section">
              {loadingAnalysis && <p>{t('intelligence.drawing.loading')}</p>}
              {drawingStatus && (
                <span className="documents-processing-badge">
                  {t(`intelligence.drawing.processing.${drawingStatus}` as never, {
                    defaultValue: drawingStatus,
                  })}
                </span>
              )}
              {drawingAnalysis?.preview_status === 'ready' && canDownload ? (
                <div className="documents-preview">
                  <iframe title={document.title} src={drawingPreviewUrl(document.id)} className="documents-preview__frame" />
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
                  <div><dt>{t('intelligence.drawing.sheets')}</dt><dd>{drawingAnalysis.sheet_count ?? 0}</dd></div>
                  <div><dt>{t('intelligence.drawing.lowConfidence')}</dt><dd>{drawingAnalysis.low_confidence_count}</dd></div>
                </dl>
              )}
              {drawingAnalysis?.summary && (
                <p>{locale === 'en' ? drawingAnalysis.summary_en ?? drawingAnalysis.summary : drawingAnalysis.summary}</p>
              )}
              <div className="documents-intelligence-actions">
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
              </div>
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
            </section>
          )}

            <section className="documents-intelligence-section">
              {loadingAnalysis && <p>{t('intelligence.loading')}</p>}
              {!loadingAnalysis && !summaryText && <p>{t('intelligence.emptySummary')}</p>}
              {summaryText && (
                <>
                  <p className="documents-disclaimer">{t('intelligence.disclaimer')}</p>
                  <p>{summaryText}</p>
                  <button type="button" className="leads__button leads__button--ghost" onClick={() => navigator.clipboard.writeText(summaryText)}>
                    {t('intelligence.copySummary')}
                  </button>
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
              {analysis?.extracted_dates?.length ? (
                <div>
                  <h3>{t('intelligence.fields.dates')}</h3>
                  <ul>{analysis.extracted_dates.map((item, index) => <li key={`date-${index}`}>{String(item.value ?? '')}</li>)}</ul>
                </div>
              ) : null}
              {analysis?.extracted_amounts?.length ? (
                <div>
                  <h3>{t('intelligence.fields.amounts')}</h3>
                  <ul>{analysis.extracted_amounts.map((item, index) => <li key={`amount-${index}`}>{String(item.amount ?? item.value ?? '')}</li>)}</ul>
                </div>
              ) : null}
              {analysis?.extracted_obligations?.length ? (
                <div>
                  <h3>{t('intelligence.fields.obligations')}</h3>
                  <ul>{analysis.extracted_obligations.map((item, index) => <li key={`obligation-${index}`}>{String(item.description ?? '')}</li>)}</ul>
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
              <button type="button" className="leads__button leads__button--primary" disabled={actionPending} onClick={() => void handleAsk()}>
                {t('intelligence.askSubmit')}
              </button>
              {askResult && (
                <div className="documents-ask-result">
                  <p>{askResult.answer}</p>
                  {askResult.source_references.length > 0 && (
                    <ul>
                      {askResult.source_references.map((ref, index) => (
                        <li key={`ref-${index}`}>{ref.reference}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </section>
          )}

          {activeTab === 'versions' && (
            <section className="documents-versions">
              {versions.length === 0 ? <p>{t('noVersions')}</p> : (
                <ul>
                  {versions.map((version) => (
                    <li key={version.id}>
                      <strong>v{version.version_number}</strong> — {version.original_file_name}
                      <span>{formatDocumentDate(version.created_at, locale)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {activeTab === 'related' && (
            <section className="documents-related">
              {document.links.length === 0 ? <p>{tCommon('noValue')}</p> : (
                <ul>{document.links.map((link) => <li key={link.id}>{link.entity_type}: {link.entity_id}</li>)}</ul>
              )}
            </section>
          )}

          {activeTab === 'activity' && (
            <EntityActivityTimeline entityType="document" entityId={document.id} title={t('activityTitle')} />
          )}
        </div>

        <footer className="leads-drawer__footer">
          <button type="button" className="leads__button leads__button--ghost" disabled={actionPending} onClick={() => void handleReprocess()}>
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
          {canDownload && (
            <a className="leads__button leads__button--secondary" href={documentDownloadUrl(document.id)} target="_blank" rel="noreferrer">
              {t('download')}
            </a>
          )}
          <button type="button" className="leads__button leads__button--ghost" onClick={() => void exportDocumentAnalysis(document.id)}>
            {t('intelligence.export')}
          </button>
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
