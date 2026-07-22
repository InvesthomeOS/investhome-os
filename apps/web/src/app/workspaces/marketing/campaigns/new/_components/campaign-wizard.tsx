'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState } from '@investhome/ui';

import { useAuth } from '@/lib/auth/auth-context';
import { canCreateCampaigns } from '@/lib/marketing/marketing-permissions';
import { createCampaign, type CampaignInput } from '@/workspaces/marketing/api/campaigns';
import { CAMPAIGN_WIZARD_STEPS } from '@/workspaces/marketing/types';
import { useCampaignUiStore } from '@/workspaces/marketing/stores/campaign-ui-store';

const EMPTY_DRAFT: CampaignInput = {
  name: '',
  objective: 'lead_generation',
  campaign_type: 'lead_generation',
  priority: 'normal',
  budget_currency: 'USD',
};

export function CampaignWizard() {
  const t = useTranslations('marketing.campaigns.wizard');
  const tSteps = useTranslations('marketing.campaigns.wizard.steps');
  const router = useRouter();
  const { user } = useAuth();
  const { wizardStep, setWizardStep, draftStorageKey, resetWizard } = useCampaignUiStore();
  const [draft, setDraft] = useState<CampaignInput>(EMPTY_DRAFT);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(draftStorageKey);
      if (saved) setDraft(JSON.parse(saved) as CampaignInput);
    } catch {
      /* ignore */
    }
  }, [draftStorageKey]);

  const saveDraft = useCallback(
    (next: CampaignInput) => {
      setDraft(next);
      localStorage.setItem(draftStorageKey, JSON.stringify(next));
    },
    [draftStorageKey],
  );

  const createMutation = useMutation({
    mutationFn: () => createCampaign(draft),
    onSuccess: (data) => {
      localStorage.removeItem(draftStorageKey);
      resetWizard();
      router.push(`/workspaces/marketing/campaigns/${data.campaign.id}` as Route);
    },
  });

  if (!canCreateCampaigns(user)) {
    return (
      <main className="dashboard marketing-wizard-page">
        <EmptyState title={t('accessDenied')} />
      </main>
    );
  }

  const step = CAMPAIGN_WIZARD_STEPS[wizardStep];
  const isLast = wizardStep === CAMPAIGN_WIZARD_STEPS.length - 1;

  const update = (patch: Partial<CampaignInput>) => saveDraft({ ...draft, ...patch });

  return (
    <main className="dashboard marketing-wizard-page">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
      </header>
      <div className="marketing-wizard">
      <div className="marketing-wizard__steps">
        {CAMPAIGN_WIZARD_STEPS.map((s, i) => (
          <span
            key={s}
            className={
              i === wizardStep
                ? 'marketing-wizard__step marketing-wizard__step--active'
                : i < wizardStep
                  ? 'marketing-wizard__step marketing-wizard__step--done'
                  : 'marketing-wizard__step'
            }
          >
            {tSteps(s)}
          </span>
        ))}
      </div>

      <div className="marketing-wizard__form">
        {step === 'basics' && (
          <>
            <div className="marketing-wizard__field">
              <label htmlFor="name">{t('fields.name')}</label>
              <input id="name" value={draft.name} onChange={(e) => update({ name: e.target.value })} required />
            </div>
            <div className="marketing-wizard__field">
              <label htmlFor="code">{t('fields.code')}</label>
              <input id="code" value={draft.code ?? ''} onChange={(e) => update({ code: e.target.value || null })} />
            </div>
            <div className="marketing-wizard__field">
              <label htmlFor="description">{t('fields.description')}</label>
              <textarea
                id="description"
                rows={3}
                value={draft.description ?? ''}
                onChange={(e) => update({ description: e.target.value || null })}
              />
            </div>
          </>
        )}

        {step === 'objective' && (
          <>
            <div className="marketing-wizard__field">
              <label htmlFor="objective">{t('fields.objective')}</label>
              <select id="objective" value={draft.objective} onChange={(e) => update({ objective: e.target.value })}>
                {['awareness', 'lead_generation', 'conversion', 'traffic', 'engagement', 'revenue'].map((o) => (
                  <option key={o} value={o}>
                    {t(`objectives.${o}` as 'objectives.awareness')}
                  </option>
                ))}
              </select>
            </div>
            <div className="marketing-wizard__field">
              <label htmlFor="campaign_type">{t('fields.type')}</label>
              <select
                id="campaign_type"
                value={draft.campaign_type}
                onChange={(e) => update({ campaign_type: e.target.value })}
              >
                {['lead_generation', 'property_launch', 'project_launch', 'brand_awareness', 'retargeting', 'other'].map(
                  (type) => (
                    <option key={type} value={type}>
                      {t(`types.${type}` as 'types.other')}
                    </option>
                  ),
                )}
              </select>
            </div>
          </>
        )}

        {(step === 'projects' || step === 'audience' || step === 'channels') && (
          <p className="marketing-campaign-card__meta">{t(`hints.${step}` as 'hints.projects')}</p>
        )}

        {step === 'schedule' && (
          <>
            <div className="marketing-wizard__field">
              <label htmlFor="start_date">{t('fields.startDate')}</label>
              <input
                id="start_date"
                type="date"
                value={draft.start_date?.slice(0, 10) ?? ''}
                onChange={(e) => update({ start_date: e.target.value ? `${e.target.value}T00:00:00Z` : null })}
              />
            </div>
            <div className="marketing-wizard__field">
              <label htmlFor="end_date">{t('fields.endDate')}</label>
              <input
                id="end_date"
                type="date"
                value={draft.end_date?.slice(0, 10) ?? ''}
                onChange={(e) => update({ end_date: e.target.value ? `${e.target.value}T00:00:00Z` : null })}
              />
            </div>
          </>
        )}

        {step === 'budget' && (
          <>
            <div className="marketing-wizard__field">
              <label htmlFor="budget_amount">{t('fields.budgetAmount')}</label>
              <input
                id="budget_amount"
                type="number"
                min="0"
                value={draft.budget_amount ?? ''}
                onChange={(e) => update({ budget_amount: e.target.value || null })}
              />
            </div>
            <div className="marketing-wizard__field">
              <label htmlFor="budget_currency">{t('fields.budgetCurrency')}</label>
              <input
                id="budget_currency"
                value={draft.budget_currency ?? 'USD'}
                onChange={(e) => update({ budget_currency: e.target.value })}
              />
            </div>
          </>
        )}

        {step === 'ownership' && (
          <div className="marketing-wizard__field">
            <label htmlFor="priority">{t('fields.priority')}</label>
            <select id="priority" value={draft.priority} onChange={(e) => update({ priority: e.target.value })}>
              {['low', 'normal', 'high', 'urgent'].map((p) => (
                <option key={p} value={p}>
                  {t(`priorities.${p}` as 'priorities.normal')}
                </option>
              ))}
            </select>
          </div>
        )}

        {(step === 'tracking' || step === 'approvals' || step === 'targets') && (
          <p className="marketing-campaign-card__meta">{t(`hints.${step}` as 'hints.tracking')}</p>
        )}

        {step === 'review' && (
          <div>
            <h3>{t('reviewTitle')}</h3>
            <dl>
              <dt>{t('fields.name')}</dt>
              <dd>{draft.name || '—'}</dd>
              <dt>{t('fields.objective')}</dt>
              <dd>{draft.objective}</dd>
              <dt>{t('fields.type')}</dt>
              <dd>{draft.campaign_type}</dd>
              <dt>{t('fields.budgetAmount')}</dt>
              <dd>{draft.budget_amount ? `${draft.budget_amount} ${draft.budget_currency}` : t('notSet')}</dd>
            </dl>
          </div>
        )}
      </div>

      <div className="marketing-wizard__actions">
        <Button
          variant="ghost"
          onClick={() => (wizardStep > 0 ? setWizardStep(wizardStep - 1) : router.push('/workspaces/marketing/campaigns' as Route))}
        >
          {wizardStep > 0 ? t('back') : t('cancel')}
        </Button>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Button variant="secondary" onClick={() => localStorage.setItem(draftStorageKey, JSON.stringify(draft))}>
            {t('saveDraft')}
          </Button>
          {isLast ? (
            <Button onClick={() => createMutation.mutate()} disabled={!draft.name || createMutation.isPending}>
              {t('createCampaign')}
            </Button>
          ) : (
            <Button onClick={() => setWizardStep(wizardStep + 1)} disabled={step === 'basics' && !draft.name}>
              {t('next')}
            </Button>
          )}
        </div>
      </div>
      </div>

      {createMutation.isError && (
        <ErrorState
          title={t('createFailed')}
          message={createMutation.error instanceof Error ? createMutation.error.message : t('createFailed')}
        />
      )}
    </main>
  );
}
