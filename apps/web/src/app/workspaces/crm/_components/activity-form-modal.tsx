'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import { activityMutations, activityQueryKeys } from '@/workspaces/crm/hooks/use-activities';
import type { ActivityInput, CrmActivityType } from '@/workspaces/crm/types/activities';
import { CRM_ACTIVITY_PRIORITIES, CRM_ACTIVITY_ENTITY_TYPES } from '@/workspaces/crm/types/activities';

type ActivityFormModalProps = {
  open: boolean;
  onClose: () => void;
  defaultType?: CrmActivityType;
  defaultEntityId?: string;
  defaultEntityType?: ActivityInput['entity_type'];
  mode?: 'activity' | 'task' | 'note' | 'meeting' | 'follow-up';
};

export function ActivityFormModal({
  open,
  onClose,
  defaultType = 'note',
  defaultEntityId,
  defaultEntityType = 'contact',
  mode = 'activity',
}: ActivityFormModalProps) {
  const t = useTranslations('crm.activities.form');
  const tCommon = useTranslations('common');
  const queryClient = useQueryClient();

  const contactsQuery = useQuery({
    ...contactQueries.list({ page: 1, page_size: 50 }),
    enabled: open,
  });

  const [entityType, setEntityType] = useState<ActivityInput['entity_type']>(defaultEntityType);
  const [entityId, setEntityId] = useState(defaultEntityId ?? '');
  const [activityType, setActivityType] = useState<CrmActivityType>(defaultType);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<ActivityInput['priority']>('medium');
  const [dueDate, setDueDate] = useState('');
  const [startDate, setStartDate] = useState('');
  const [visibility, setVisibility] = useState<ActivityInput['visibility']>('organization');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setEntityType(defaultEntityType);
      setEntityId(defaultEntityId ?? '');
      setActivityType(defaultType);
      setTitle('');
      setDescription('');
      setError(null);
    }
  }, [open, defaultEntityId, defaultEntityType, defaultType]);

  useEffect(() => {
    if (!entityId && contactsQuery.data?.items[0]) {
      setEntityId(contactsQuery.data.items[0].id);
    }
  }, [contactsQuery.data, entityId]);

  const createMutation = useMutation({
    mutationFn: async (payload: ActivityInput) => {
      if (mode === 'task') return activityMutations.createTask(payload);
      if (mode === 'note') return activityMutations.createNote(payload);
      if (mode === 'meeting') return activityMutations.createMeeting(payload);
      return activityMutations.create(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: activityQueryKeys.all });
      await queryClient.invalidateQueries({ queryKey: ['crm', 'timeline'] });
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!open) return null;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!entityId || !title.trim()) {
      setError(t('validationRequired'));
      return;
    }
    createMutation.mutate({
      entity_type: entityType,
      entity_id: entityId,
      activity_type: activityType,
      title: title.trim(),
      description: description.trim() || undefined,
      priority,
      due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
      start_date: startDate ? new Date(startDate).toISOString() : undefined,
      visibility,
    });
  };

  return (
    <div className="crm-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="crm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="activity-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="crm-modal__header">
          <h2 id="activity-form-title">{t(`modes.${mode}` as 'modes.activity')}</h2>
          <button type="button" className="crm-modal__close" onClick={onClose} aria-label={tCommon('close')}>
            ×
          </button>
        </header>

        {contactsQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : (
          <form className="crm-modal__form" onSubmit={handleSubmit}>
            {error && <ErrorState title={t('saveFailed')} message={error} />}

            <label className="crm-form-field">
              <span>{t('entityType')}</span>
              <select value={entityType} onChange={(e) => setEntityType(e.target.value as ActivityInput['entity_type'])}>
                {CRM_ACTIVITY_ENTITY_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>

            <label className="crm-form-field">
              <span>{t('entity')}</span>
              <select value={entityId} onChange={(e) => setEntityId(e.target.value)} required>
                <option value="">{t('selectEntity')}</option>
                {contactsQuery.data?.items.map((contact) => (
                  <option key={contact.id} value={contact.id}>
                    {contact.display_name}
                  </option>
                ))}
              </select>
            </label>

            {mode === 'activity' && (
              <label className="crm-form-field">
                <span>{t('activityType')}</span>
                <select value={activityType} onChange={(e) => setActivityType(e.target.value as CrmActivityType)}>
                  <option value="note">note</option>
                  <option value="phone_call">phone_call</option>
                  <option value="email">email</option>
                  <option value="meeting">meeting</option>
                  <option value="task">task</option>
                  <option value="follow_up">follow_up</option>
                </select>
              </label>
            )}

            <label className="crm-form-field">
              <span>{t('title')}</span>
              <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={500} />
            </label>

            <label className="crm-form-field">
              <span>{t('description')}</span>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
            </label>

            <div className="crm-form-row">
              <label className="crm-form-field">
                <span>{t('priority')}</span>
                <select value={priority} onChange={(e) => setPriority(e.target.value as ActivityInput['priority'])}>
                  {CRM_ACTIVITY_PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
              <label className="crm-form-field">
                <span>{t('visibility')}</span>
                <select
                  value={visibility}
                  onChange={(e) => setVisibility(e.target.value as ActivityInput['visibility'])}
                >
                  <option value="organization">{t('visibilityOrganization')}</option>
                  <option value="team">{t('visibilityTeam')}</option>
                  <option value="private">{t('visibilityPrivate')}</option>
                </select>
              </label>
            </div>

            {(mode === 'task' || mode === 'follow-up') && (
              <label className="crm-form-field">
                <span>{t('dueDate')}</span>
                <input type="datetime-local" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </label>
            )}

            {mode === 'meeting' && (
              <label className="crm-form-field">
                <span>{t('startDate')}</span>
                <input type="datetime-local" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </label>
            )}

            <footer className="crm-modal__footer">
              <Button type="button" variant="secondary" onClick={onClose}>
                {tCommon('cancel')}
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? tCommon('saving') : tCommon('save')}
              </Button>
            </footer>
          </form>
        )}
      </div>
    </div>
  );
}
