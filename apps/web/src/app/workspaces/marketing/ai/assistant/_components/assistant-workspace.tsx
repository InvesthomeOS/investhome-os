'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useEffect, useState, useTransition } from 'react';

import { useAuth } from '@/lib/auth/auth-context';
import {
  canSaveMarketingAI,
  canUseMarketingAI,
  canViewMarketingAI,
} from '@/lib/marketing/marketing-permissions';
import {
  archiveAssistantOutput,
  fetchAssistantModes,
  generateAssistantOutput,
  saveAssistantOutput,
} from '@/workspaces/marketing/api/assistant';
import {
  createClientRequestId,
  modeRequiresCampaign,
  modeRequiresSourceText,
  type AssistantMode,
  type AssistantModesResponse,
  type AssistantOutput,
} from '@/workspaces/marketing/schemas/assistant';

import { AIPageShell } from '../../_components/ai-shell';

type UiState =
  | 'idle'
  | 'loading_modes'
  | 'generating'
  | 'ready'
  | 'empty'
  | 'missing_context'
  | 'permission'
  | 'provider_unavailable'
  | 'timeout'
  | 'safety'
  | 'error';

const MODE_KEYS: AssistantMode[] = [
  'marketing_summary',
  'campaign_analysis',
  'content_draft',
  'campaign_brief',
  'audience_suggestion',
  'channel_suggestion',
  'translation',
  'next_actions',
];

function plainText(value: string): string {
  return value.replace(/<[^>]*>/g, '');
}

export function AssistantWorkspace() {
  const t = useTranslations('marketing.ai.assistant');
  const { user, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const initialMode = (searchParams.get('mode') as AssistantMode | null) || 'marketing_summary';
  const initialCampaignId = searchParams.get('campaignId') || '';
  const initialProjectId = searchParams.get('projectId') || '';
  const initialAssetId = searchParams.get('assetId') || '';
  const initialLang = (searchParams.get('lang') as 'tr' | 'en' | null) || 'en';

  const [modes, setModes] = useState<AssistantModesResponse | null>(null);
  const [mode, setMode] = useState<AssistantMode>(
    MODE_KEYS.includes(initialMode) ? initialMode : 'marketing_summary',
  );
  const [campaignId, setCampaignId] = useState(initialCampaignId);
  const [projectId, setProjectId] = useState(initialProjectId);
  const [assetIds, setAssetIds] = useState(initialAssetId);
  const [language, setLanguage] = useState<'tr' | 'en'>(initialLang === 'tr' ? 'tr' : 'en');
  const [targetLanguage, setTargetLanguage] = useState<'tr' | 'en'>(initialLang === 'tr' ? 'en' : 'tr');
  const [tone, setTone] = useState('professional');
  const [contentType, setContentType] = useState('social_media_post');
  const [channel, setChannel] = useState('');
  const [sourceText, setSourceText] = useState('');
  const [instruction, setInstruction] = useState('');
  const [callToAction, setCallToAction] = useState('');
  const [output, setOutput] = useState<AssistantOutput | null>(null);
  const [uiState, setUiState] = useState<UiState>('loading_modes');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copyDone, setCopyDone] = useState(false);
  const [lastRequestId, setLastRequestId] = useState<string | null>(null);

  const canView = canViewMarketingAI(user);
  const canUse = canUseMarketingAI(user);
  const canSave = canSaveMarketingAI(user);

  useEffect(() => {
    if (authLoading) return;
    if (!canView) {
      setUiState('permission');
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchAssistantModes();
        if (cancelled) return;
        setModes(data);
        if (!data.provider_available) {
          setUiState('provider_unavailable');
        } else {
          setUiState('idle');
        }
      } catch {
        if (!cancelled) {
          setUiState('error');
          setErrorMessage(t('errors.loadModes'));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, canView, t]);

  function validateContext(): boolean {
    if (modeRequiresCampaign(mode) && !campaignId.trim()) {
      setUiState('missing_context');
      setErrorMessage(t('errors.campaignRequired'));
      return false;
    }
    if (modeRequiresSourceText(mode) && !sourceText.trim()) {
      setUiState('missing_context');
      setErrorMessage(t('errors.sourceTextRequired'));
      return false;
    }
    return true;
  }

  function handleGenerate(regenerateOfId?: string) {
    if (!canUse) {
      setUiState('permission');
      return;
    }
    if (!validateContext()) return;
    if (isPending || uiState === 'generating') return;

    const requestId = regenerateOfId && lastRequestId ? `${lastRequestId}-regen` : createClientRequestId();
    setLastRequestId(requestId);
    setUiState('generating');
    setErrorMessage(null);
    setCopyDone(false);

    startTransition(async () => {
      try {
        const result = await generateAssistantOutput({
          mode,
          campaign_id: campaignId.trim() || null,
          project_id: projectId.trim() || null,
          asset_ids: assetIds
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          language,
          target_language: mode === 'translation' ? targetLanguage : null,
          tone: mode === 'content_draft' ? tone : null,
          content_type: mode === 'content_draft' ? contentType : null,
          channel: channel.trim() || null,
          source_text: mode === 'translation' ? sourceText : null,
          adaptation_style: mode === 'translation' ? 'professional' : null,
          call_to_action: callToAction.trim() || null,
          user_instruction: instruction.trim() || null,
          client_request_id: requestId,
          regenerate_of_id: regenerateOfId || null,
        });
        setOutput(result);
        if (result.safety_blocked) {
          setUiState('safety');
        } else {
          setUiState('ready');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : t('errors.generateFailed');
        if (message.toLowerCase().includes('timeout') || message.includes('504')) {
          setUiState('timeout');
        } else if (message.toLowerCase().includes('unavailable') || message.includes('503')) {
          setUiState('provider_unavailable');
        } else if (message.includes('403')) {
          setUiState('permission');
        } else {
          setUiState('error');
        }
        setErrorMessage(message);
      }
    });
  }

  async function handleSave() {
    if (!output || !canSave) return;
    const saved = await saveAssistantOutput(output.id, {
      title: output.title || undefined,
      generated_content: output.generated_content,
    });
    setOutput(saved);
  }

  async function handleArchive() {
    if (!output || !canSave) return;
    const archived = await archiveAssistantOutput(output.id);
    setOutput(archived);
  }

  async function handleCopy() {
    if (!output) return;
    await navigator.clipboard.writeText(plainText(output.generated_content));
    setCopyDone(true);
  }

  if (authLoading) {
    return (
      <AIPageShell title={t('title')} subtitle={t('subtitle')}>
        <p className="mkt-ai-assistant__state">{t('states.loading')}</p>
      </AIPageShell>
    );
  }

  if (uiState === 'permission' || !canView) {
    return (
      <AIPageShell title={t('title')} subtitle={t('subtitle')}>
        <section className="mkt-ai-assistant__state mkt-ai-assistant__state--permission">
          <h2>{t('states.permissionTitle')}</h2>
          <p>{t('states.permissionHint')}</p>
        </section>
      </AIPageShell>
    );
  }

  return (
    <AIPageShell title={t('title')} subtitle={t('subtitle')}>
      <div className="mkt-ai-assistant">
        <p className="mkt-ai-assistant__disclaimer">{t('disclaimer')}</p>

        <section className="mkt-ai-assistant__panel">
          <h2 className="mkt-ai-assistant__section-title">{t('modeLabel')}</h2>
          <div className="mkt-ai-assistant__modes" role="listbox" aria-label={t('modeLabel')}>
            {MODE_KEYS.map((key) => (
              <button
                key={key}
                type="button"
                role="option"
                aria-selected={mode === key}
                className={
                  mode === key
                    ? 'mkt-ai-assistant__mode mkt-ai-assistant__mode--active'
                    : 'mkt-ai-assistant__mode'
                }
                onClick={() => {
                  setMode(key);
                  setUiState(modes?.provider_available === false ? 'provider_unavailable' : 'idle');
                  setErrorMessage(null);
                }}
              >
                {t(`modes.${key}` as 'modes.marketing_summary')}
              </button>
            ))}
          </div>
        </section>

        <section className="mkt-ai-assistant__panel">
          <h2 className="mkt-ai-assistant__section-title">{t('contextLabel')}</h2>
          <div className="mkt-ai-assistant__grid">
            <label>
              {t('fields.campaignId')}
              <input value={campaignId} onChange={(e) => setCampaignId(e.target.value)} />
            </label>
            <label>
              {t('fields.projectId')}
              <input value={projectId} onChange={(e) => setProjectId(e.target.value)} />
            </label>
            <label>
              {t('fields.assetIds')}
              <input
                value={assetIds}
                onChange={(e) => setAssetIds(e.target.value)}
                placeholder={t('fields.assetIdsHint')}
              />
            </label>
            <label>
              {t('fields.language')}
              <select value={language} onChange={(e) => setLanguage(e.target.value as 'tr' | 'en')}>
                <option value="en">English</option>
                <option value="tr">Türkçe</option>
              </select>
            </label>
            {mode === 'content_draft' ? (
              <>
                <label>
                  {t('fields.contentType')}
                  <select value={contentType} onChange={(e) => setContentType(e.target.value)}>
                    {(modes?.content_draft_types || [contentType]).map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {t('fields.tone')}
                  <select value={tone} onChange={(e) => setTone(e.target.value)}>
                    {(modes?.tones || [tone]).map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            ) : null}
            {mode === 'translation' ? (
              <>
                <label>
                  {t('fields.targetLanguage')}
                  <select
                    value={targetLanguage}
                    onChange={(e) => setTargetLanguage(e.target.value as 'tr' | 'en')}
                  >
                    <option value="en">English</option>
                    <option value="tr">Türkçe</option>
                  </select>
                </label>
                <label className="mkt-ai-assistant__full">
                  {t('fields.sourceText')}
                  <textarea value={sourceText} onChange={(e) => setSourceText(e.target.value)} rows={5} />
                </label>
              </>
            ) : null}
            <label>
              {t('fields.channel')}
              <input value={channel} onChange={(e) => setChannel(e.target.value)} />
            </label>
            <label>
              {t('fields.callToAction')}
              <input value={callToAction} onChange={(e) => setCallToAction(e.target.value)} />
            </label>
            <label className="mkt-ai-assistant__full">
              {t('fields.instruction')}
              <textarea value={instruction} onChange={(e) => setInstruction(e.target.value)} rows={3} />
            </label>
          </div>

          <div className="mkt-ai-assistant__actions">
            <button
              type="button"
              className="mkt-ai-assistant__primary"
              disabled={!canUse || uiState === 'generating' || isPending || uiState === 'provider_unavailable'}
              onClick={() => handleGenerate()}
            >
              {uiState === 'generating' ? t('actions.generating') : t('actions.generate')}
            </button>
            {!canUse ? <span className="mkt-ai-assistant__hint">{t('states.useDenied')}</span> : null}
          </div>
        </section>

        {uiState === 'provider_unavailable' ? (
          <section className="mkt-ai-assistant__state">{t('states.providerUnavailable')}</section>
        ) : null}
        {uiState === 'timeout' ? <section className="mkt-ai-assistant__state">{t('states.timeout')}</section> : null}
        {uiState === 'missing_context' ? (
          <section className="mkt-ai-assistant__state">{errorMessage || t('states.missingContext')}</section>
        ) : null}
        {uiState === 'error' ? (
          <section className="mkt-ai-assistant__state">{errorMessage || t('errors.generateFailed')}</section>
        ) : null}
        {uiState === 'idle' && !output ? (
          <section className="mkt-ai-assistant__state">{t('states.empty')}</section>
        ) : null}
        {uiState === 'generating' ? (
          <section className="mkt-ai-assistant__state" aria-busy="true">
            {t('states.generating')}
          </section>
        ) : null}

        {output ? (
          <section className="mkt-ai-assistant__panel mkt-ai-assistant__result">
            <header className="mkt-ai-assistant__result-header">
              <div>
                <h2>{output.title || t('resultTitle')}</h2>
                <p>
                  {t('statusLabel')}: {output.status.toUpperCase()} · {output.prompt_key} ·{' '}
                  {output.model_provider}/{output.model_name}
                </p>
              </div>
              <div className="mkt-ai-assistant__result-actions">
                <button type="button" onClick={handleCopy}>
                  {copyDone ? t('actions.copied') : t('actions.copy')}
                </button>
                <button type="button" onClick={() => handleGenerate(output.id)} disabled={!canUse}>
                  {t('actions.regenerate')}
                </button>
                <button type="button" onClick={handleSave} disabled={!canSave}>
                  {t('actions.save')}
                </button>
                <button type="button" onClick={handleArchive} disabled={!canSave}>
                  {t('actions.archive')}
                </button>
              </div>
            </header>

            {uiState === 'safety' || output.safety_blocked ? (
              <div className="mkt-ai-assistant__safety" role="alert">
                <strong>{t('states.safetyTitle')}</strong>
                <p>{output.safety_message || t('states.safetyHint')}</p>
                {output.safety_flags?.length ? (
                  <ul>
                    {output.safety_flags.map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}

            <pre className="mkt-ai-assistant__content">{plainText(output.generated_content)}</pre>

            <div className="mkt-ai-assistant__meta">
              <div>
                <h3>{t('dataSources')}</h3>
                {output.data_sources?.length ? (
                  <ul>
                    {output.data_sources.map((source, idx) => (
                      <li key={`${source.kind}-${idx}`}>
                        {String(source.kind)}: {String(source.label)}
                        {source.detail ? ` — ${String(source.detail)}` : ''}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>{t('noDataSources')}</p>
                )}
              </div>
              <div>
                <h3>{t('missingData')}</h3>
                {output.data_warnings?.length ? (
                  <ul>
                    {output.data_warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                ) : (
                  <p>{t('noMissingData')}</p>
                )}
              </div>
              <div>
                <h3>{t('assumptions')}</h3>
                {output.assumptions?.length ? (
                  <ul>
                    {output.assumptions.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                ) : (
                  <p>{t('noAssumptions')}</p>
                )}
              </div>
            </div>

            {output.action_links?.length ? (
              <div className="mkt-ai-assistant__links">
                <h3>{t('nextActions')}</h3>
                <ul>
                  {output.action_links.map((link) => (
                    <li key={`${link.href}-${link.label}`}>
                      <Link href={link.href as Route}>{link.label}</Link>
                      {link.reason ? <span> — {link.reason}</span> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
    </AIPageShell>
  );
}
