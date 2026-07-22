'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import { createAutomation } from '@/workspaces/marketing/hooks/use-automations';

const TRIGGER_OPTIONS = ['lead_created', 'form_submitted', 'manual'] as const;
const ACTION_OPTIONS = ['notify_team', 'create_task', 'send_email'] as const;

export default function AutomationWizardPage() {
  const t = useTranslations('marketing.automations.wizard');
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [triggerType, setTriggerType] = useState<string>(TRIGGER_OPTIONS[0]);
  const [actionType, setActionType] = useState<string>(ACTION_OPTIONS[0]);
  const [submitting, setSubmitting] = useState(false);

  async function handleCreate() {
    setSubmitting(true);
    try {
      const automation = await createAutomation({
        name,
        description: description || undefined,
        trigger: { type: triggerType, config: {} },
        conditions: [],
        actions: [{ type: actionType, config: {} }],
      });
      router.push(`/workspaces/marketing/automations/${automation.id}` as Route);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="dashboard marketing-automation-wizard">
      <h1>{t('title')}</h1>
      <label>
        {t('name')}
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label>
        {t('description')}
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label>
        {t('trigger')}
        <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
          {TRIGGER_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t('action')}
        <select value={actionType} onChange={(e) => setActionType(e.target.value)}>
          {ACTION_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
      <Button disabled={!name || submitting} onClick={handleCreate}>
        {t('create')}
      </Button>
    </main>
  );
}
