'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import { createSegment } from '@/workspaces/marketing/hooks/use-segments';

export default function SegmentWizardPage() {
  const t = useTranslations('marketing.segments.wizard');
  const router = useRouter();
  const [name, setName] = useState('');

  async function handleCreate() {
    const segment = await createSegment({
      name,
      segment_type: 'dynamic',
      rule_groups: [{ operator: 'and', rules: [] }],
    });
    router.push(`/workspaces/marketing/segments/${segment.id}` as Route);
  }

  return (
    <main className="dashboard">
      <h1>{t('title')}</h1>
      <label>
        {t('name')}
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <Button disabled={!name} onClick={handleCreate}>
        {t('create')}
      </Button>
    </main>
  );
}
