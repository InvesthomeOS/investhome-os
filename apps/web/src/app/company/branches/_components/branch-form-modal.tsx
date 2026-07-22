'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import type { BranchDetail, BranchInput, BranchStatus, BranchType } from '@/lib/api/branches';
import { fetchCompanies, type CompanyListItem } from '@/lib/api/companies';

type BranchFormModalProps = {
  open: boolean;
  mode: 'create' | 'edit';
  initial?: BranchDetail | null;
  onClose: () => void;
  onSubmit: (payload: BranchInput) => Promise<void>;
  saving: boolean;
  error?: string | null;
};

const BRANCH_TYPES: BranchType[] = [
  'head_office',
  'regional_office',
  'corporate_office',
  'sales_office',
  'construction_office',
  'project_office',
  'warehouse',
  'service_center',
  'temporary_office',
  'remote_office',
  'other',
];

const BRANCH_STATUSES: BranchStatus[] = [
  'planning',
  'opening_soon',
  'active',
  'inactive',
  'temporarily_closed',
  'closed',
  'archived',
];

function emptyForm(): BranchInput {
  return {
    branch_code: '',
    branch_name: '',
    company_id: '',
    branch_type: 'other',
    country: '',
    city: '',
    full_address: '',
    status: 'planning',
  };
}

export function BranchFormModal({
  open,
  mode,
  initial,
  onClose,
  onSubmit,
  saving,
  error,
}: BranchFormModalProps) {
  const t = useTranslations('company.branches');
  const tTypes = useTranslations('company.branches.types');
  const tStatuses = useTranslations('company.branches.statuses');
  const [form, setForm] = useState<BranchInput>(emptyForm());
  const [companies, setCompanies] = useState<CompanyListItem[]>([]);

  useEffect(() => {
    if (!open) return;
    fetchCompanies({ page: 1, page_size: 100, sort_by: 'company_name', sort_order: 'asc' })
      .then((response) => setCompanies(response.items))
      .catch(() => setCompanies([]));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (mode === 'edit' && initial) {
      setForm({
        branch_code: initial.branch_code,
        branch_name: initial.branch_name,
        company_id: initial.company_id,
        branch_type: initial.branch_type,
        country: initial.country,
        state: initial.state,
        city: initial.city,
        district: initial.district,
        postal_code: initial.postal_code,
        full_address: initial.full_address,
        latitude: initial.latitude,
        longitude: initial.longitude,
        google_maps_link: initial.google_maps_link,
        timezone: initial.timezone,
        main_phone: initial.main_phone,
        mobile_phone: initial.mobile_phone,
        email: initial.email,
        website: initial.website,
        emergency_contact: initial.emergency_contact,
        manager_user_id: initial.manager_user_id,
        status: initial.status,
        opening_date: initial.opening_date,
        department_count: initial.department_count,
        notes: initial.notes,
      });
      return;
    }
    setForm(emptyForm());
  }, [open, mode, initial]);

  if (!open) return null;

  const update = <K extends keyof BranchInput>(key: K, value: BranchInput[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await onSubmit(form);
  };

  return (
    <div className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="branch-form-title">
      <div className="admin-modal__backdrop" onClick={onClose} />
      <form className="admin-modal__panel admin-modal__panel--wide" onSubmit={handleSubmit}>
        <header className="admin-modal__header">
          <h2 id="branch-form-title">{mode === 'create' ? t('createBranch') : t('editBranch')}</h2>
          <button type="button" className="admin-modal__close" onClick={onClose} aria-label={t('close')}>×</button>
        </header>
        <div className="admin-modal__body admin-modal__body--grid">
          <label>
            <span>{t('fields.branch_code')}</span>
            <input required value={form.branch_code} onChange={(e) => update('branch_code', e.target.value)} />
          </label>
          <label>
            <span>{t('fields.branch_name')}</span>
            <input required value={form.branch_name} onChange={(e) => update('branch_name', e.target.value)} />
          </label>
          <label>
            <span>{t('fields.company')}</span>
            <select required value={form.company_id} onChange={(e) => update('company_id', e.target.value)}>
              <option value="">{t('selectCompany')}</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>{company.company_name}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('fields.branch_type')}</span>
            <select value={form.branch_type} onChange={(e) => update('branch_type', e.target.value as BranchType)}>
              {BRANCH_TYPES.map((value) => (
                <option key={value} value={value}>{tTypes(value)}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('fields.status')}</span>
            <select value={form.status ?? 'planning'} onChange={(e) => update('status', e.target.value as BranchStatus)}>
              {BRANCH_STATUSES.map((value) => (
                <option key={value} value={value}>{tStatuses(value)}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('fields.country')}</span>
            <input required value={form.country} onChange={(e) => update('country', e.target.value)} />
          </label>
          <label>
            <span>{t('fields.state')}</span>
            <input value={form.state ?? ''} onChange={(e) => update('state', e.target.value || null)} />
          </label>
          <label>
            <span>{t('fields.city')}</span>
            <input required value={form.city} onChange={(e) => update('city', e.target.value)} />
          </label>
          <label>
            <span>{t('fields.district')}</span>
            <input value={form.district ?? ''} onChange={(e) => update('district', e.target.value || null)} />
          </label>
          <label>
            <span>{t('fields.postal_code')}</span>
            <input value={form.postal_code ?? ''} onChange={(e) => update('postal_code', e.target.value || null)} />
          </label>
          <label className="admin-modal__field--full">
            <span>{t('fields.full_address')}</span>
            <textarea required rows={2} value={form.full_address} onChange={(e) => update('full_address', e.target.value)} />
          </label>
          <label>
            <span>{t('fields.latitude')}</span>
            <input type="number" step="any" value={form.latitude ?? ''} onChange={(e) => update('latitude', e.target.value ? Number(e.target.value) : null)} />
          </label>
          <label>
            <span>{t('fields.longitude')}</span>
            <input type="number" step="any" value={form.longitude ?? ''} onChange={(e) => update('longitude', e.target.value ? Number(e.target.value) : null)} />
          </label>
          <label className="admin-modal__field--full">
            <span>{t('fields.google_maps_link')}</span>
            <input value={form.google_maps_link ?? ''} onChange={(e) => update('google_maps_link', e.target.value || null)} />
          </label>
          <label>
            <span>{t('fields.main_phone')}</span>
            <input value={form.main_phone ?? ''} onChange={(e) => update('main_phone', e.target.value || null)} />
          </label>
          <label>
            <span>{t('fields.email')}</span>
            <input type="email" value={form.email ?? ''} onChange={(e) => update('email', e.target.value || null)} />
          </label>
          <label className="admin-modal__field--full">
            <span>{t('fields.notes')}</span>
            <textarea rows={3} value={form.notes ?? ''} onChange={(e) => update('notes', e.target.value || null)} />
          </label>
        </div>
        {error ? <p className="admin-modal__error">{error}</p> : null}
        <footer className="admin-modal__footer">
          <Button type="button" variant="secondary" onClick={onClose}>{t('cancel')}</Button>
          <Button type="submit" disabled={saving}>{saving ? t('saving') : t('save')}</Button>
        </footer>
      </form>
    </div>
  );
}
