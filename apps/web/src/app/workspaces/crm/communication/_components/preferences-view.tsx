'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Alert, Button, Input, LoadingState, Select } from '@investhome/ui';

import { hasCrmPermission } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { upsertCommunicationPreferences } from '@/workspaces/crm/api/communication';

export function PreferencesView() {
  const t = useTranslations('crm.communication.preferences');
  const tChannels = useTranslations('crm.communication.channels');
  const tCommon = useTranslations('common');
  const { authLoading, user, canViewCommunications } = useCrmAccess();
  const canEdit = hasCrmPermission(user, 'edit_communications');
  const [entityId, setEntityId] = useState('');
  const [entityType, setEntityType] = useState<'contact' | 'company'>('contact');
  const [preferredChannel, setPreferredChannel] = useState('email');
  const [doNotContact, setDoNotContact] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      upsertCommunicationPreferences(entityType, entityId, {
        preferred_channel: preferredChannel as 'email',
        do_not_contact: doNotContact,
        consent_email: !doNotContact,
      }),
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <Alert tone="error">{t('accessDenied')}</Alert>;
  }

  return (
    <div className="crm-communication-subview">
      <header className="crm-communication-subview__header">
        <h2>{t('title')}</h2>
        <p>{t('subtitle')}</p>
      </header>

      <form
        className="crm-communication-subview__form"
        onSubmit={(e) => {
          e.preventDefault();
          if (canEdit && entityId) mutation.mutate();
        }}
      >
        <label className="crm-form-field">
          <span>{t('fields.entityType')}</span>
          <Select value={entityType} onChange={(e) => setEntityType(e.target.value as 'contact' | 'company')}>
            <option value="contact">{t('entityTypes.contact')}</option>
            <option value="company">{t('entityTypes.company')}</option>
          </Select>
        </label>
        <label className="crm-form-field">
          <span>{t('fields.entityId')}</span>
          <Input value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="UUID" />
        </label>
        <label className="crm-form-field">
          <span>{t('fields.preferredChannel')}</span>
          <Select value={preferredChannel} onChange={(e) => setPreferredChannel(e.target.value)}>
            <option value="email">{tChannels('email')}</option>
            <option value="whatsapp">{tChannels('whatsapp')}</option>
            <option value="sms">{tChannels('sms')}</option>
            <option value="phone">{tChannels('phone')}</option>
          </Select>
        </label>
        <label className="crm-form-field">
          <input type="checkbox" checked={doNotContact} onChange={(e) => setDoNotContact(e.target.checked)} />
          <span>{t('fields.doNotContact')}</span>
        </label>
        {canEdit ? (
          <Button type="submit" disabled={!entityId || mutation.isPending}>{t('save')}</Button>
        ) : (
          <Alert tone="warning">{t('readOnly')}</Alert>
        )}
        {mutation.isSuccess && <Alert tone="success">{t('saved')}</Alert>}
      </form>
    </div>
  );
}
