'use client';

import { Button, Dialog, Input, Select } from '@investhome/ui';
import { useTranslations } from 'next-intl';
import type { FormEvent } from 'react';

import type { CompanyEntityType, CompanyRecord, CompanyStatus } from '@/lib/api/companies';

type CompanyFormModalProps = {
  open: boolean;
  mode: 'create' | 'edit';
  initial?: CompanyRecord | null;
  onClose: () => void;
  onSubmit: (payload: Record<string, string>) => Promise<void>;
};

const ENTITY_TYPES: CompanyEntityType[] = [
  'corporation',
  'llc',
  'lp',
  'llp',
  'holding',
  'trust',
  'branch',
  'subsidiary',
  'joint_venture',
  'foundation',
  'non_profit',
  'other',
];

const STATUSES: CompanyStatus[] = [
  'draft',
  'pending_review',
  'active',
  'inactive',
  'suspended',
  'closed',
  'archived',
];

export function CompanyFormModal({ open, mode, initial, onClose, onSubmit }: CompanyFormModalProps) {
  const t = useTranslations('company.companies');
  const tCommon = useTranslations('common');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: Record<string, string> = {};
    form.forEach((value, key) => {
      payload[key] = String(value);
    });
    await onSubmit(payload);
  };

  if (!open) {
    return null;
  }

  return (
    <Dialog open={open} onClose={onClose} title={mode === 'create' ? t('actions.create') : t('actions.edit')}>
      <form className="auth-form company-form" onSubmit={(event) => void handleSubmit(event)}>
        <label>
          {t('fields.companyName')}
          <Input name="company_name" defaultValue={initial?.company_name ?? ''} required />
        </label>
        <label>
          {t('fields.legalName')}
          <Input name="legal_name" defaultValue={initial?.legal_name ?? ''} />
        </label>
        <label>
          {t('fields.entityType')}
          <Select name="entity_type" defaultValue={initial?.entity_type ?? 'other'}>
            {ENTITY_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`entityTypes.${type}` as 'entityTypes.other')}
              </option>
            ))}
          </Select>
        </label>
        <label>
          {t('fields.registrationNumber')}
          <Input name="registration_number" defaultValue={initial?.registration_number ?? ''} />
        </label>
        <label>
          {t('fields.taxId')}
          <Input name="tax_id" defaultValue={initial?.tax_id ?? ''} />
        </label>
        <label>
          {t('fields.country')}
          <Input name="country" defaultValue={initial?.country ?? ''} />
        </label>
        <label>
          {t('fields.state')}
          <Input name="state" defaultValue={initial?.state ?? ''} />
        </label>
        <label>
          {t('fields.city')}
          <Input name="city" defaultValue={initial?.city ?? ''} />
        </label>
        <label>
          {t('fields.industry')}
          <Input name="industry" defaultValue={initial?.industry ?? ''} />
        </label>
        <label>
          {t('fields.status')}
          <Select name="status" defaultValue={initial?.status ?? 'draft'}>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {t(`statuses.${status}` as 'statuses.draft')}
              </option>
            ))}
          </Select>
        </label>
        <label>
          {t('fields.notes')}
          <Input name="notes" defaultValue={initial?.notes ?? ''} />
        </label>
        <div className="company-form__actions">
          <Button type="button" variant="secondary" onClick={onClose}>
            {tCommon('cancel')}
          </Button>
          <Button type="submit">{mode === 'create' ? t('actions.create') : tCommon('save')}</Button>
        </div>
      </form>
    </Dialog>
  );
}
