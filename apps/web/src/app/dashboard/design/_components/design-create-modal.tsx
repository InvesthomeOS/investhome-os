'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  createDesignProject,
  fetchCompatibleSourceDocuments,
  type CompatibleSourceDocument,
  type DesignProject,
  type DesignProjectInput,
  type DesignType,
} from '@/lib/api/design';
import { drawingPreviewUrl } from '@/lib/api/drawing-intelligence';
import type { Project } from '@/lib/api/projects';
import { useDesignLabels } from '@/lib/i18n/design-labels';

interface DesignCreateModalProps {
  projects: Project[];
  onClose: () => void;
  onCreated: (design: DesignProject) => void;
}

export function DesignCreateModal({ projects, onClose, onCreated }: DesignCreateModalProps) {
  const t = useTranslations('design.create');
  const tCommon = useTranslations('common');
  const { typeOptions } = useDesignLabels();

  const [projectId, setProjectId] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [designType, setDesignType] = useState<DesignType>('colored_floor_plan');
  const [documents, setDocuments] = useState<CompatibleSourceDocument[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedDocument = documents.find((doc) => doc.id === documentId) ?? null;

  const loadDocuments = useCallback(async (nextProjectId: string) => {
    if (!nextProjectId) {
      setDocuments([]);
      return;
    }
    setLoadingDocs(true);
    try {
      const response = await fetchCompatibleSourceDocuments(nextProjectId);
      setDocuments(response.items);
    } catch {
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments(projectId);
    setDocumentId('');
  }, [projectId, loadDocuments]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectId || !documentId || !title.trim()) {
      setError(t('validationRequired'));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const input: DesignProjectInput = {
        project_id: projectId,
        document_id: documentId,
        drawing_analysis_id: selectedDocument?.drawing_analysis_id ?? undefined,
        title: title.trim(),
        description: description.trim() || undefined,
        design_type: designType,
      };
      const created = await createDesignProject(input);
      onCreated(created);
    } catch {
      setError(t('submitError'));
      setSubmitting(false);
    }
  };

  return (
    <div className="leads-modal" role="dialog" aria-modal="true" aria-labelledby="design-create-title">
      <div className="leads-modal__backdrop" onClick={onClose} />
      <div className="leads-modal__panel design-create">
        <header className="leads-modal__header">
          <h2 id="design-create-title">{t('title')}</h2>
          <button type="button" className="leads-modal__close" onClick={onClose} aria-label={tCommon('close')}>
            ×
          </button>
        </header>

        <form className="leads-form" onSubmit={(event) => void handleSubmit(event)}>
          <div className="leads-form__grid">
            <label className="leads-form__field">
              <span>{t('project')}</span>
              <select
                required
                value={projectId}
                onChange={(event) => setProjectId(event.target.value)}
              >
                <option value="">{t('selectProject')}</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.project_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads-form__field">
              <span>{t('sourceDocument')}</span>
              <select
                required
                value={documentId}
                disabled={!projectId || loadingDocs}
                onChange={(event) => setDocumentId(event.target.value)}
              >
                <option value="">{loadingDocs ? tCommon('loading') : t('selectDocument')}</option>
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.title}
                    {doc.has_room_regions ? ` (${t('hasRegions')})` : ''}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads-form__field">
              <span>{t('designType')}</span>
              <select value={designType} onChange={(event) => setDesignType(event.target.value as DesignType)}>
                {typeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="leads-form__field leads-form__field--full">
              <span>{t('titleLabel')}</span>
              <input required value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>

            <label className="leads-form__field leads-form__field--full">
              <span>{t('descriptionLabel')}</span>
              <textarea rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
            </label>
          </div>

          {selectedDocument && (
            <div className="design-create__preview">
              <h3 className="leads-form__section-title">{t('sourcePreview')}</h3>
              {selectedDocument.preview_status === 'ready' ? (
                <iframe
                  title={selectedDocument.title}
                  src={drawingPreviewUrl(selectedDocument.id)}
                  className="documents-preview__frame"
                />
              ) : (
                <p className="leads__state">{t('previewUnavailable')}</p>
              )}
            </div>
          )}

          {error && <p className="leads-form__error">{error}</p>}

          <footer className="leads-modal__footer">
            <button type="button" className="leads__button leads__button--secondary" onClick={onClose}>
              {tCommon('cancel')}
            </button>
            <button type="submit" className="leads__button leads__button--primary" disabled={submitting}>
              {submitting ? tCommon('loading') : t('submit')}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
