'use client';

import { useState } from 'react';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import { Button } from '@investhome/ui';

import { createSocialPost } from '@/workspaces/marketing/api/social';

export default function NewSocialPostPage() {
  const t = useTranslations('marketing.channels.social');
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');

  const mutation = useMutation({
    mutationFn: () => createSocialPost({ title, body_text: body }),
    onSuccess: (post) => router.push(`/workspaces/marketing/social/posts/${post.id}` as Route),
  });

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('create')}</h1>
      </header>
      <form
        className="marketing-form"
        onSubmit={(e) => {
          e.preventDefault();
          void mutation.mutate();
        }}
      >
        <label>
          {t('fields.title')}
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          {t('fields.body')}
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6} />
        </label>
        <Button type="submit" disabled={mutation.isPending}>
          {t('fields.saveDraft')}
        </Button>
      </form>
    </main>
  );
}
