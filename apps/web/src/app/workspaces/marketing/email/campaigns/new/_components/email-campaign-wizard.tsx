'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { fetchAudiences } from '@/workspaces/marketing/api/audiences';
import {
  createEmailCampaign,
  emailQueryKeys,
  fetchEmailDashboard,
  fetchEmailSenders,
  fetchEmailTemplates,
  updateEmailCampaign,
} from '@/workspaces/marketing/api/email';
import { EMAIL_CAMPAIGN_WIZARD_STEPS, type EmailCampaignWizardDraft } from '@/workspaces/marketing/types';

const DRAFT_STORAGE_KEY = 'marketing.emailCampaignWizard.draft';

const EMPTY_DRAFT: EmailCampaignWizardDraft = {
  name: '',
  subject: null,
  preview_text: null,
  audience_id: null,
  marketing_campaign_id: null,
  content_id: null,
  template_id: null,
  sender_profile_id: null,
  scheduled_at: null,
  unsubscribe_required: true,
  unsubscribe_link_present: false,
  wizard_state_json: null,
};

export function EmailCampaignWizard() {
  const t = useTranslations('marketing.email.wizard');
  const tSteps = useTranslations('marketing.email.wizard.steps');
  const tCommon = useTranslations('marketing.common');
  const router = useRouter();
  const { user } = useAuth();
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState<EmailCampaignWizardDraft>(EMPTY_DRAFT);
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [savedNotice, setSavedNotice] = useState(false);

  const dashboardQuery = useQuery({ queryKey: emailQueryKeys.dashboard(), queryFn: () => fetchEmailDashboard() });
  const audiencesQuery = useQuery({ queryKey: ['marketing', 'audiences', 'wizard'], queryFn: () => fetchAudiences({ page_size: 100 }) });
  const templatesQuery = useQuery({ queryKey: emailQueryKeys.templates(), queryFn: () => fetchEmailTemplates() });
  const sendersQuery = useQuery({ queryKey: emailQueryKeys.senders(), queryFn: () => fetchEmailSenders() });

  useEffect(() => {
    try {
      const saved = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as { draft: EmailCampaignWizardDraft; campaignId?: string | null; stepIndex?: number };
        setDraft(parsed.draft);
        setCampaignId(parsed.campaignId ?? null);
        setStepIndex(parsed.stepIndex ?? 0);
      }
    } catch {
      /* ignore corrupt draft */
    }
  }, []);

  const saveDraftLocal = useCallback(
    (next: EmailCampaignWizardDraft, nextStep = stepIndex, nextCampaignId = campaignId) => {
      setDraft(next);
      localStorage.setItem(
        DRAFT_STORAGE_KEY,
        JSON.stringify({ draft: next, campaignId: nextCampaignId, stepIndex: nextStep }),
      );
      setSavedNotice(true);
      window.setTimeout(() => setSavedNotice(false), 2000);
    },
    [campaignId, stepIndex],
  );

  const update = (patch: Partial<EmailCampaignWizardDraft>) => saveDraftLocal({ ...draft, ...patch });

  const persistMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: draft.name.trim(),
        subject: draft.subject,
        preview_text: draft.preview_text,
        audience_id: draft.audience_id,
        marketing_campaign_id: draft.marketing_campaign_id,
        content_id: draft.content_id,
        template_id: draft.template_id,
        sender_profile_id: draft.sender_profile_id,
        unsubscribe_required: draft.unsubscribe_required,
        unsubscribe_link_present: draft.unsubscribe_link_present,
        wizard_step: stepIndex + 1,
        wizard_state_json: { step: EMAIL_CAMPAIGN_WIZARD_STEPS[stepIndex], ...draft.wizard_state_json },
      };
      if (campaignId) {
        return updateEmailCampaign(campaignId, payload);
      }
      return createEmailCampaign(payload);
    },
    onSuccess: (campaign) => {
      setCampaignId(campaign.id);
      saveDraftLocal(draft, stepIndex, campaign.id);
    },
  });

  const finishMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: draft.name.trim(),
        subject: draft.subject,
        preview_text: draft.preview_text,
        audience_id: draft.audience_id,
        template_id: draft.template_id,
        sender_profile_id: draft.sender_profile_id,
        scheduled_at: draft.scheduled_at,
        unsubscribe_required: draft.unsubscribe_required,
        unsubscribe_link_present: draft.unsubscribe_link_present,
        wizard_step: EMAIL_CAMPAIGN_WIZARD_STEPS.length,
      };
      if (campaignId) {
        return updateEmailCampaign(campaignId, payload);
      }
      return createEmailCampaign(payload);
    },
    onSuccess: (campaign) => {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
      router.push(`/workspaces/marketing/email/campaigns/${campaign.id}` as Route);
    },
  });

  if (!hasMarketingPermission(user, 'send_email')) {
    return (
      <main className="dashboard marketing-wizard-page">
        <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />
      </main>
    );
  }

  const providerConnected = dashboardQuery.data?.provider_status?.connected ?? false;
  const step = EMAIL_CAMPAIGN_WIZARD_STEPS[stepIndex]!;
  const isLast = stepIndex === EMAIL_CAMPAIGN_WIZARD_STEPS.length - 1;
  const canAdvanceBasics = draft.name.trim().length > 0;

  return (
    <main className="dashboard marketing-wizard-page">
      <header className="dashboard__header">
        <Link href={'/workspaces/marketing/email' as Route}>{t('back')}</Link>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">
          {t('step')} {stepIndex + 1} / {EMAIL_CAMPAIGN_WIZARD_STEPS.length}: {tSteps(step)}
        </p>
        {!providerConnected ? <p className="marketing-integration-setup__note">{t('providerNotConnected')}</p> : null}
      </header>

      <div className="marketing-wizard">
        <div className="marketing-wizard__steps">
          {EMAIL_CAMPAIGN_WIZARD_STEPS.map((wizardStep, index) => (
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
            <div className="marketing-wizard__field">
              <label htmlFor="email-campaign-name">{t('fields.name')}</label>
              <input id="email-campaign-name" value={draft.name} onChange={(e) => update({ name: e.target.value })} required />
            </div>
          )}

          {step === 'objective' && (
            <div className="marketing-wizard__field">
              <label htmlFor="email-objective">{t('fields.objective')}</label>
              <select
                id="email-objective"
                value={String((draft.wizard_state_json as { objective?: string } | null)?.objective ?? 'lead_generation')}
                onChange={(e) => update({ wizard_state_json: { ...(draft.wizard_state_json ?? {}), objective: e.target.value } })}
              >
                {['awareness', 'lead_generation', 'conversion', 'nurture'].map((objective) => (
                  <option key={objective} value={objective}>
                    {t(`objectives.${objective}` as 'objectives.awareness')}
                  </option>
                ))}
              </select>
            </div>
          )}

          {step === 'audience' && (
            <div className="marketing-wizard__field">
              <label htmlFor="email-audience">{t('fields.audience')}</label>
              <select
                id="email-audience"
                value={draft.audience_id ?? ''}
                onChange={(e) => update({ audience_id: e.target.value || null })}
              >
                <option value="">{t('fields.audiencePlaceholder')}</option>
                {(audiencesQuery.data?.items ?? []).map((audience) => (
                  <option key={audience.id} value={audience.id}>
                    {audience.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {step === 'sender' && (
            <div className="marketing-wizard__field">
              <label htmlFor="email-sender">{t('fields.sender')}</label>
              <select
                id="email-sender"
                value={draft.sender_profile_id ?? ''}
                onChange={(e) => update({ sender_profile_id: e.target.value || null })}
              >
                <option value="">{t('fields.senderPlaceholder')}</option>
                {(sendersQuery.data ?? []).map((sender) => (
                  <option key={sender.id} value={sender.id}>
                    {sender.from_name} &lt;{sender.from_email}&gt;
                  </option>
                ))}
              </select>
            </div>
          )}

          {step === 'subject' && (
            <div className="marketing-wizard__field">
              <label htmlFor="email-subject">{t('fields.subject')}</label>
              <input id="email-subject" value={draft.subject ?? ''} onChange={(e) => update({ subject: e.target.value || null })} />
            </div>
          )}

          {step === 'preview' && (
            <div className="marketing-wizard__field">
              <label htmlFor="email-preview">{t('fields.preview')}</label>
              <input
                id="email-preview"
                value={draft.preview_text ?? ''}
                onChange={(e) => update({ preview_text: e.target.value || null })}
              />
            </div>
          )}

          {step === 'content' && <p className="marketing-campaign-card__meta">{t('hints.content')}</p>}

          {step === 'template' && (
            <div className="marketing-wizard__field">
              <label htmlFor="email-template">{t('fields.template')}</label>
              <select
                id="email-template"
                value={draft.template_id ?? ''}
                onChange={(e) => update({ template_id: e.target.value || null })}
              >
                <option value="">{t('fields.templatePlaceholder')}</option>
                {(templatesQuery.data ?? []).map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {step === 'scheduling' && (
            <div className="marketing-wizard__field">
              <label htmlFor="email-schedule">{t('fields.scheduledAt')}</label>
              <input
                id="email-schedule"
                type="datetime-local"
                value={draft.scheduled_at?.slice(0, 16) ?? ''}
                onChange={(e) => update({ scheduled_at: e.target.value ? `${e.target.value}:00Z` : null })}
              />
            </div>
          )}

          {step === 'tracking' && <p className="marketing-campaign-card__meta">{t('hints.tracking')}</p>}

          {step === 'consent' && (
            <div className="marketing-wizard__field">
              <label>
                <input
                  type="checkbox"
                  checked={draft.unsubscribe_required}
                  onChange={(e) => update({ unsubscribe_required: e.target.checked })}
                />
                {t('fields.unsubscribeRequired')}
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={draft.unsubscribe_link_present}
                  onChange={(e) => update({ unsubscribe_link_present: e.target.checked })}
                />
                {t('fields.unsubscribeLinkPresent')}
              </label>
            </div>
          )}

          {step === 'personalisation' && <p className="marketing-campaign-card__meta">{t('hints.personalisation')}</p>}

          {(step === 'review' || step === 'confirm') && (
            <dl className="marketing-kv-list">
              <div className="marketing-kv-list__row">
                <dt>{t('fields.name')}</dt>
                <dd>{draft.name}</dd>
              </div>
              <div className="marketing-kv-list__row">
                <dt>{t('fields.subject')}</dt>
                <dd>{draft.subject ?? tCommon('noData')}</dd>
              </div>
              <div className="marketing-kv-list__row">
                <dt>{t('fields.audience')}</dt>
                <dd>{draft.audience_id ?? tCommon('noData')}</dd>
              </div>
            </dl>
          )}

          {(persistMutation.isError || finishMutation.isError) && (
            <ErrorState
              title={tCommon('error')}
              message={
                (persistMutation.error ?? finishMutation.error) instanceof ApiError
                  ? ((persistMutation.error ?? finishMutation.error) as ApiError).message
                  : tCommon('error')
              }
            />
          )}
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
            <Button type="button" disabled={!canAdvanceBasics || finishMutation.isPending} onClick={() => void finishMutation.mutate()}>
              {t('create')}
            </Button>
          )}
          <Button type="button" variant="secondary" disabled={persistMutation.isPending || !canAdvanceBasics} onClick={() => void persistMutation.mutate()}>
            {t('saveDraft')}
          </Button>
          <Link href={'/workspaces/marketing/email' as Route} className="button button--secondary">
            {t('cancel')}
          </Link>
          {savedNotice || persistMutation.isSuccess ? <span className="marketing-wizard__saved">{t('draftSaved')}</span> : null}
        </div>
      </div>
    </main>
  );
}