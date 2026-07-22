'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { createAudience } from '@/workspaces/marketing/api/audiences';
import { AUDIENCE_WIZARD_STEPS, type AudienceWizardDraft } from '@/workspaces/marketing/types';

const DRAFT_STORAGE_KEY = 'marketing.audienceWizard.draft';

const EMPTY_DRAFT: AudienceWizardDraft = {
  name: '',
  description: null,
  mode: 'static',
  audience_type: 'static',
  language: null,
  contact_ids: [],
  segment_ids: [],
  consent_requirements_json: null,
  channel_ids: [],
  geo_json: null,
  exclusion_refs_json: null,
  refresh_policy_json: null,
};

export function AudienceWizard() {
  const t = useTranslations('marketing.audiences.wizard');
  const tSteps = useTranslations('marketing.audiences.wizard.steps');
  const tCommon = useTranslations('marketing.common');
  const router = useRouter();
  const { user } = useAuth();
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState<AudienceWizardDraft>(EMPTY_DRAFT);
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (saved) setDraft(JSON.parse(saved) as AudienceWizardDraft);
    } catch {
      /* ignore corrupt draft */
    }
  }, []);

  const saveDraft = useCallback((next: AudienceWizardDraft) => {
    setDraft(next);
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(next));
    setSavedNotice(true);
    window.setTimeout(() => setSavedNotice(false), 2000);
  }, []);

  const update = (patch: Partial<AudienceWizardDraft>) => saveDraft({ ...draft, ...patch });

  const createMutation = useMutation({
    mutationFn: () =>
      createAudience({
        name: draft.name.trim(),
        description: draft.description,
        audience_type: draft.audience_type,
        mode: draft.mode,
        language: draft.language,
        contact_ids: draft.contact_ids.length ? draft.contact_ids : null,
        segment_ids: draft.segment_ids.length ? draft.segment_ids : null,
        consent_requirements_json: draft.consent_requirements_json,
        channel_ids: draft.channel_ids.length ? draft.channel_ids : null,
        geo_json: draft.geo_json,
        exclusion_refs_json: draft.exclusion_refs_json,
        refresh_policy_json: draft.refresh_policy_json,
      }),
    onSuccess: (audience) => {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
      router.push(`/workspaces/marketing/audiences/${audience.id}` as Route);
    },
  });

  if (!hasMarketingPermission(user, 'create')) {
    return (
      <main className="dashboard marketing-wizard-page">
        <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />
      </main>
    );
  }

  const step = AUDIENCE_WIZARD_STEPS[stepIndex]!;
  const isLast = stepIndex === AUDIENCE_WIZARD_STEPS.length - 1;
  const canAdvanceBasics = draft.name.trim().length > 0;

  return (
    <main className="dashboard marketing-wizard-page marketing-audience-wizard">
      <header className="dashboard__header">
        <Link href={'/workspaces/marketing/audiences' as Route}>{t('back')}</Link>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">
          {t('step')} {stepIndex + 1} / {AUDIENCE_WIZARD_STEPS.length}: {tSteps(step)}
        </p>
      </header>

      <div className="marketing-wizard">
        <div className="marketing-wizard__steps">
          {AUDIENCE_WIZARD_STEPS.map((wizardStep, index) => (
            <span
              key={wizardStep}
              className={
                index === stepIndex
                  ? 'marketing-wizard__step marketing-wizard__step--active'
                  : index < stepIndex
                    ? 'marketing-wizard__step marketing-wizard__step--done'
                    : 'marketing-wizard__step'
              }
            >
              {tSteps(wizardStep)}
            </span>
          ))}
        </div>

        <div className="marketing-wizard__form">
          {step === 'basics' && (
            <>
              <div className="marketing-wizard__field">
                <label htmlFor="audience-name">{t('fields.name')}</label>
                <input id="audience-name" value={draft.name} onChange={(e) => update({ name: e.target.value })} required />
              </div>
              <div className="marketing-wizard__field">
                <label htmlFor="audience-description">{t('fields.description')}</label>
                <textarea
                  id="audience-description"
                  rows={3}
                  value={draft.description ?? ''}
                  onChange={(e) => update({ description: e.target.value || null })}
                />
              </div>
              <div className="marketing-wizard__field">
                <label htmlFor="audience-language">{t('fields.language')}</label>
                <input
                  id="audience-language"
                  value={draft.language ?? ''}
                  onChange={(e) => update({ language: e.target.value || null })}
                />
              </div>
            </>
          )}

          {step === 'mode' && (
            <div className="marketing-wizard__field">
              <label htmlFor="audience-mode">{t('fields.mode')}</label>
              <select
                id="audience-mode"
                value={draft.mode}
                onChange={(e) => {
                  const mode = e.target.value;
                  update({
                    mode,
                    audience_type: mode === 'dynamic' ? 'dynamic' : mode === 'hybrid' ? 'hybrid' : 'static',
                  });
                }}
              >
                {['static', 'dynamic', 'hybrid', 'provider_synced'].map((mode) => (
                  <option key={mode} value={mode}>
                    {t(`modes.${mode}` as 'modes.static')}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(step === 'contacts' || step === 'segments' || step === 'channels') && (
            <p className="marketing-campaign-card__meta">{t(`hints.${step}` as 'hints.contacts')}</p>
          )}

          {step === 'consent' && (
            <div className="marketing-wizard__field">
              <label htmlFor="consent-policy">{t('fields.consentPolicy')}</label>
              <select
                id="consent-policy"
                value={String((draft.consent_requirements_json as { policy?: string } | null)?.policy ?? 'marketing')}
                onChange={(e) => update({ consent_requirements_json: { policy: e.target.value } })}
              >
                {['marketing', 'transactional', 'mixed'].map((policy) => (
                  <option key={policy} value={policy}>
                    {t(`consentPolicies.${policy}` as 'consentPolicies.marketing')}
                  </option>
                ))}
              </select>
            </div>
          )}

          {step === 'geo' && (
            <div className="marketing-wizard__field">
              <label htmlFor="geo-region">{t('fields.geoRegion')}</label>
              <input
                id="geo-region"
                value={String((draft.geo_json as { region?: string } | null)?.region ?? '')}
                onChange={(e) => update({ geo_json: { region: e.target.value || null } })}
              />
            </div>
          )}

          {step === 'exclusions' && (
            <div className="marketing-wizard__field">
              <label htmlFor="exclusion-note">{t('fields.exclusionNote')}</label>
              <textarea
                id="exclusion-note"
                rows={3}
                value={String((draft.exclusion_refs_json as { note?: string } | null)?.note ?? '')}
                onChange={(e) => update({ exclusion_refs_json: { note: e.target.value || null } })}
              />
            </div>
          )}

          {step === 'refresh' && (
            <div className="marketing-wizard__field">
              <label htmlFor="refresh-cadence">{t('fields.refreshCadence')}</label>
              <select
                id="refresh-cadence"
                value={String((draft.refresh_policy_json as { cadence?: string } | null)?.cadence ?? 'manual')}
                onChange={(e) => update({ refresh_policy_json: { cadence: e.target.value } })}
              >
                {['manual', 'daily', 'weekly'].map((cadence) => (
                  <option key={cadence} value={cadence}>
                    {t(`refreshCadences.${cadence}` as 'refreshCadences.manual')}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(step === 'review' || step === 'confirm') && (
            <dl className="marketing-kv-list">
              <div className="marketing-kv-list__row">
                <dt>{t('fields.name')}</dt>
                <dd>{draft.name}</dd>
              </div>
              <div className="marketing-kv-list__row">
                <dt>{t('fields.mode')}</dt>
                <dd>{draft.mode}</dd>
              </div>
              <div className="marketing-kv-list__row">
                <dt>{t('fields.language')}</dt>
                <dd>{draft.language ?? tCommon('noData')}</dd>
              </div>
            </dl>
          )}

          {createMutation.isError ? (
            <ErrorState
              title={tCommon('error')}
              message={createMutation.error instanceof ApiError ? createMutation.error.message : tCommon('error')}
            />
          ) : null}
        </div>

        <div className="marketing-wizard__actions">
          <Button type="button" variant="secondary" disabled={stepIndex === 0} onClick={() => setStepIndex((index) => index - 1)}>
            {t('prev')}
          </Button>
          {!isLast ? (
            <Button
              type="button"
              disabled={step === 'basics' && !canAdvanceBasics}
              onClick={() => setStepIndex((index) => index + 1)}
            >
              {t('next')}
            </Button>
          ) : (
            <Button type="button" disabled={!canAdvanceBasics || createMutation.isPending} onClick={() => void createMutation.mutate()}>
              {t('create')}
            </Button>
          )}
          <Button type="button" variant="secondary" onClick={() => saveDraft(draft)}>
            {t('saveDraft')}
          </Button>
          <Link href={'/workspaces/marketing/audiences' as Route} className="button button--secondary">
            {t('cancel')}
          </Link>
          {savedNotice ? <span className="marketing-wizard__saved">{t('draftSaved')}</span> : null}
        </div>
      </div>
    </main>
  );
}
