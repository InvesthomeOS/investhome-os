'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import { Button, Dialog, Input, Select, TextArea } from '@investhome/ui';

import { checkDuplicates, createContact, type ContactInput } from '@/workspaces/crm/api/contacts';
import { CRM_CONTACT_TYPES, type CrmContactType } from '@/workspaces/crm/types';
import { useContactUiStore } from '@/workspaces/crm/stores/contact-ui-store';

type ContactFormModalProps = {
  open: boolean;
  onClose: () => void;
  onSuccess: (contactId: string) => void;
};

function emptyForm(): ContactInput {
  return {
    contact_type: 'prospect',
    record_kind: 'person',
    display_name: '',
    primary_email: '',
    primary_phone: '',
    organization_name: '',
    notes: '',
    lifecycle_stage: 'new',
    priority: 'normal',
    status: 'active',
  };
}

export function ContactFormModal({ open, onClose, onSuccess }: ContactFormModalProps) {
  const t = useTranslations('crm.contacts.form');
  const tTypes = useTranslations('crm.contactTypes');
  const { draftStorageKey } = useContactUiStore();
  const [form, setForm] = useState<ContactInput>(emptyForm());
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const draft = sessionStorage.getItem(draftStorageKey);
    if (draft) {
      try {
        setForm({ ...emptyForm(), ...JSON.parse(draft) });
      } catch {
        setForm(emptyForm());
      }
    } else {
      setForm(emptyForm());
    }
    setError(null);
  }, [open, draftStorageKey]);

  useEffect(() => {
    if (!open) return;
    sessionStorage.setItem(draftStorageKey, JSON.stringify(form));
  }, [form, open, draftStorageKey]);

  const createMutation = useMutation({
    mutationFn: (payload: ContactInput) => createContact(payload),
    onSuccess: (result) => {
      sessionStorage.removeItem(draftStorageKey);
      onSuccess(result.contact.id);
    },
    onError: (err: Error) => setError(err.message),
  });

  const submit = async (skipDuplicateCheck = false) => {
    if (!form.display_name.trim()) {
      setError(t('displayName'));
      return;
    }
    if (!skipDuplicateCheck) {
      const dupes = await checkDuplicates({
        primary_email: form.primary_email ?? undefined,
        primary_phone: form.primary_phone ?? undefined,
        display_name: form.display_name,
        organization_name: form.organization_name ?? undefined,
      });
      if (dupes.matches.length > 0) {
        setDuplicateWarning(dupes.matches[0]?.display_name ?? '');
        return;
      }
    }
    createMutation.mutate(form);
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        title={t('title')}
        footer={
          <>
            <Button type="button" variant="secondary" onClick={onClose}>
              {t('cancel')}
            </Button>
            <Button type="button" variant="primary" onClick={() => void submit()} disabled={createMutation.isPending}>
              {t('save')}
            </Button>
          </>
        }
      >
        <div className="crm-contact-form leads-form">
          <div className="leads-form__grid crm-contact-form__row">
            <Input
              id="crm-contact-display-name"
              label={t('displayName')}
              value={form.display_name}
              onChange={(event) => setForm((prev) => ({ ...prev, display_name: event.target.value }))}
            />
            <Select
              id="crm-contact-type"
              label={t('contactType')}
              value={form.contact_type}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, contact_type: event.target.value as CrmContactType }))
              }
            >
              {CRM_CONTACT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {tTypes(type)}
                </option>
              ))}
            </Select>
          </div>
          <div className="leads-form__grid">
            <Input
              id="crm-contact-email"
              type="email"
              label={t('email')}
              value={form.primary_email ?? ''}
              onChange={(event) => setForm((prev) => ({ ...prev, primary_email: event.target.value }))}
            />
            <Input
              id="crm-contact-phone"
              label={t('phone')}
              value={form.primary_phone ?? ''}
              onChange={(event) => setForm((prev) => ({ ...prev, primary_phone: event.target.value }))}
            />
          </div>
          <Input
            id="crm-contact-organization"
            label={t('organization')}
            value={form.organization_name ?? ''}
            onChange={(event) => setForm((prev) => ({ ...prev, organization_name: event.target.value }))}
          />
          <TextArea
            id="crm-contact-notes"
            label={t('notes')}
            rows={3}
            value={form.notes ?? ''}
            onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
          />
          {error ? (
            <p className="ih-field__error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      </Dialog>

      <Dialog
        open={Boolean(duplicateWarning)}
        onClose={() => setDuplicateWarning(null)}
        title={t('duplicateTitle')}
        footer={
          <>
            <Button type="button" variant="secondary" onClick={() => setDuplicateWarning(null)}>
              {t('cancel')}
            </Button>
            <Button
              type="button"
              onClick={() => {
                setDuplicateWarning(null);
                void submit(true);
              }}
            >
              {t('saveAnyway')}
            </Button>
          </>
        }
      >
        <p>{t('duplicateMessage', { name: duplicateWarning ?? '' })}</p>
      </Dialog>
    </>
  );
}
