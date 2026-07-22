'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { audienceQueries, refreshAudience } from '@/workspaces/marketing/hooks/use-audiences';
import { updateAudience } from '@/workspaces/marketing/api/audiences';

export default function AudienceSettingsPage() {
  const params = useParams<{ audienceId: string }>();
  const t = useTranslations('marketing.audiences.settings');
  const tCommon = useTranslations('marketing.common');
  const queryClient = useQueryClient();
  const detailQuery = useQuery(audienceQueries.detail(params.audienceId));
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (detailQuery.data) {
      setName(detailQuery.data.name);
      setDescription(detailQuery.data.description ?? '');
    }
  }, [detailQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAudience(params.audienceId, {
        name: name.trim(),
        description: description.trim() || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: audienceQueries.detail(params.audienceId).queryKey });
    },
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshAudience(params.audienceId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: audienceQueries.detail(params.audienceId).queryKey });
      void queryClient.invalidateQueries({ queryKey: audienceQueries.readiness(params.audienceId).queryKey });
    },
  });

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (!detailQuery.data) return <EmptyState title={tCommon('error')} />;

  return (
    <section className="marketing-detail-panel marketing-audience-settings">
      <form
        className="marketing-wizard__form"
        onSubmit={(event) => {
          event.preventDefault();
          void saveMutation.mutate();
        }}
      >
        <div className="marketing-wizard__field">
          <label htmlFor="audience-name">{t('fields.name')}</label>
          <input id="audience-name" value={name} onChange={(event) => setName(event.target.value)} required />
        </div>
        <div className="marketing-wizard__field">
          <label htmlFor="audience-description">{t('fields.description')}</label>
          <textarea
            id="audience-description"
            rows={4}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>
        {saveMutation.isError ? (
          <p className="marketing-form__error" role="alert">
            {saveMutation.error instanceof ApiError ? saveMutation.error.message : tCommon('error')}
          </p>
        ) : null}
        {saveMutation.isSuccess ? <p className="marketing-form__success">{t('saved')}</p> : null}
        <div className="marketing-wizard__actions">
          <Button type="submit" disabled={saveMutation.isPending || !name.trim()}>
            {t('save')}
          </Button>
          <Button type="button" variant="secondary" disabled={refreshMutation.isPending} onClick={() => void refreshMutation.mutate()}>
            {t('refresh')}
          </Button>
        </div>
      </form>
    </section>
  );
}
