'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import { Button } from '@investhome/ui';

import { createContent } from '@/workspaces/marketing/api/content';
import { CONTENT_WIZARD_STEPS, type ContentWizardStep } from '@/workspaces/marketing/types';

export function ContentCreationWizard() {
  const t = useTranslations('marketing.content.wizard');
  const router = useRouter();
  const [stepIndex, setStepIndex] = useState(0);
  const [title, setTitle] = useState('');
  const [contentType, setContentType] = useState('blog_post');
  const [description, setDescription] = useState('');

  const step = CONTENT_WIZARD_STEPS[stepIndex] as ContentWizardStep;

  const createMutation = useMutation({
    mutationFn: () => createContent({ title, content_type: contentType, description }),
    onSuccess: (data) => {
      router.push(`/workspaces/marketing/content/${data.content.id}` as Route);
    },
  });

  const isLastStep = stepIndex === CONTENT_WIZARD_STEPS.length - 1;

  return (
    <main className="dashboard marketing-content-wizard">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      <ol className="marketing-content-wizard__steps">
        {CONTENT_WIZARD_STEPS.map((s, i) => (
          <li key={s} className={i === stepIndex ? 'marketing-content-wizard__step marketing-content-wizard__step--active' : 'marketing-content-wizard__step'}>
            {t(`steps.${s}` as 'steps.basics')}
          </li>
        ))}
      </ol>

      <section className="marketing-content-wizard__panel">
        {step === 'basics' && (
          <>
            <label className="marketing-field">
              <span>{t('fields.title')}</span>
              <input value={title} onChange={(e) => setTitle(e.target.value)} required />
            </label>
            <label className="marketing-field">
              <span>{t('fields.contentType')}</span>
              <select value={contentType} onChange={(e) => setContentType(e.target.value)}>
                <option value="blog_post">{t('contentTypes.blog_post')}</option>
                <option value="social_post">{t('contentTypes.social_post')}</option>
                <option value="email_template">{t('contentTypes.email_template')}</option>
                <option value="landing_page">{t('contentTypes.landing_page')}</option>
                <option value="ad_creative">{t('contentTypes.ad_creative')}</option>
              </select>
            </label>
          </>
        )}
        {step === 'brief' && (
          <label className="marketing-field">
            <span>{t('fields.description')}</span>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
          </label>
        )}
        {!['basics', 'brief'].includes(step) && (
          <p className="marketing-content-wizard__placeholder">{t('stepPlaceholder', { step: t(`steps.${step}` as 'steps.basics') })}</p>
        )}
      </section>

      <footer className="marketing-content-wizard__footer">
        <Button type="button" disabled={stepIndex === 0} onClick={() => setStepIndex((i) => i - 1)}>
          {t('back')}
        </Button>
        {isLastStep ? (
          <Button type="button" disabled={!title || createMutation.isPending} onClick={() => createMutation.mutate()}>
            {t('create')}
          </Button>
        ) : (
          <Button type="button" onClick={() => setStepIndex((i) => i + 1)}>
            {t('next')}
          </Button>
        )}
      </footer>
    </main>
  );
}
