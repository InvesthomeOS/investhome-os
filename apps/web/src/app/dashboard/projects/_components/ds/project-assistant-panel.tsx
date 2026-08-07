'use client';

import { useCallback, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  askProjectAssistant,
  type ProjectAssistantResponse,
} from '@/lib/api/project-assistant';
import { useAuth } from '@/lib/auth/auth-context';

interface ProjectAssistantPanelProps {
  projectId: string;
}

function confidenceTone(confidence: number, grounded: boolean) {
  if (!grounded || confidence < 0.35) return 'danger' as const;
  if (confidence < 0.55) return 'warning' as const;
  return 'success' as const;
}

function formatConfidence(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

export function ProjectAssistantPanel({ projectId }: ProjectAssistantPanelProps) {
  const t = useTranslations('projects.detail.assistant');
  const { user } = useAuth();
  const canAsk = hasPermission(user, 'creative_studio', 'view');

  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectAssistantResponse | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const onAsk = useCallback(async () => {
    const q = question.trim();
    if (!canAsk || !q || loading) return;
    setLoading(true);
    setError(null);
    try {
      const next = await askProjectAssistant({
        question: q,
        project_id: projectId,
        project_scope: 'single',
        conversation_id: conversationId,
      });
      setResult(next);
      setConversationId(next.conversation_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('error');
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [canAsk, conversationId, loading, projectId, question, t]);

  if (!canAsk) {
    return null;
  }

  return (
    <section
      className="proj-detail-ds__panel proj-detail-ds__assistant"
      data-testid="project-assistant-panel"
      aria-label={t('title')}
    >
      <div className="proj-detail-ds__assistant-head">
        <div>
          <h3 className="proj-detail-ds__panel-title">{t('title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('subtitle')}</p>
        </div>
        {result ? (
          <StatusChip tone={confidenceTone(result.confidence, result.grounded)}>
            {t('confidence')}: {formatConfidence(result.confidence)}
          </StatusChip>
        ) : null}
      </div>

      <label className="proj-detail-ds__assistant-label" htmlFor="project-assistant-question">
        {t('questionLabel')}
      </label>
      <textarea
        id="project-assistant-question"
        className="proj-detail-ds__assistant-input"
        data-testid="project-assistant-question"
        rows={3}
        value={question}
        disabled={loading}
        placeholder={t('placeholder')}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            void onAsk();
          }
        }}
      />

      <div className="proj-detail-ds__assistant-actions">
        <Button
          type="button"
          onClick={() => void onAsk()}
          disabled={loading || !question.trim()}
          data-testid="project-assistant-ask"
        >
          {loading ? t('asking') : t('ask')}
        </Button>
      </div>

      {loading ? (
        <p className="proj-detail-ds__assistant-loading" data-testid="project-assistant-loading">
          {t('loading')}
        </p>
      ) : null}

      {error ? (
        <div className="proj-detail-ds__drive-error" data-testid="project-assistant-error">
          <strong>{t('error')}</strong>
          <p className="proj-detail-ds__panel-sub">{error}</p>
        </div>
      ) : null}

      {result && !loading ? (
        <div className="proj-detail-ds__assistant-result" data-testid="project-assistant-result">
          <h4 className="proj-detail-ds__assistant-section-title">{t('answer')}</h4>
          <p className="proj-detail-ds__assistant-answer" data-testid="project-assistant-answer">
            {result.answer}
          </p>

          <div className="proj-detail-ds__assistant-meta">
            <span>
              {t('confidence')}: {formatConfidence(result.confidence)}
            </span>
            <span>
              {t('latency')}: {result.latency_ms}ms
            </span>
          </div>

          <h4 className="proj-detail-ds__assistant-section-title">{t('sources')}</h4>
          {result.citations.length === 0 ? (
            <p className="proj-detail-ds__panel-sub" data-testid="project-assistant-no-sources">
              {t('noSources')}
            </p>
          ) : (
            <ul className="proj-detail-ds__assistant-sources" data-testid="project-assistant-sources">
              {result.citations.map((c) => (
                <li key={c.chunk_id}>
                  <strong>{c.document_name}</strong>
                  <span>
                    {c.chunk_reference}
                    {c.asset_id ? ` · ${t('assetId')}: ${c.asset_id.slice(0, 8)}…` : ''}
                  </span>
                  {c.excerpt ? <em>{c.excerpt}</em> : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </section>
  );
}
