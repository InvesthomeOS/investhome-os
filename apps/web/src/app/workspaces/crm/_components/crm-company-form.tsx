'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, TextArea } from '@investhome/ui';

import { canCreateCrm } from '@/lib/crm/crm-permissions';
import { crmCompaniesMutations, crmCompaniesQueryKeys } from '@/lib/query/crm-companies-queries';
import { useAuth } from '@/lib/auth/auth-context';
import {
  CRM_COMPANY_TYPES,
  PROFILE_TYPES_BY_COMPANY_TYPE,
  type CrmCompanyType,
} from '@/workspaces/crm/types';
import {
  crmCompanyFormDefaults,
  crmCompanyFormSchema,
  type CrmCompanyFormValues,
} from '@/workspaces/crm/schemas/company';
import { useCrmCompaniesStore } from '@/workspaces/crm/_stores/crm-companies-store';
import { useQueryClient } from '@tanstack/react-query';
import { fetchCrmCompanies } from '@/workspaces/crm/api/companies';

const DRAFT_KEY = 'investhome-crm-company-draft';

export function CrmCompanyForm({ mode = 'create' }: { mode?: 'create' | 'edit' }) {
  const t = useTranslations('crm.companies');
  const tCrm = useTranslations('crm');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { draftFormOpen } = useCrmCompaniesStore();
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);

  const form = useForm<CrmCompanyFormValues>({
    resolver: zodResolver(crmCompanyFormSchema) as never,
    defaultValues: crmCompanyFormDefaults,
  });

  const companyType = form.watch('company_type') as CrmCompanyType;
  const profileKey = PROFILE_TYPES_BY_COMPANY_TYPE[companyType];

  useEffect(() => {
    if (mode !== 'create') return;
    const saved = localStorage.getItem(DRAFT_KEY);
    if (saved && draftFormOpen) {
      try {
        form.reset(JSON.parse(saved) as CrmCompanyFormValues);
      } catch {
        localStorage.removeItem(DRAFT_KEY);
      }
    }
  }, [draftFormOpen, form, mode]);

  useEffect(() => {
    if (mode !== 'create') return;
    const subscription = form.watch((values) => {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(values));
    });
    return () => subscription.unsubscribe();
  }, [form, mode]);

  const createMutation = useMutation({
    ...crmCompaniesMutations.create(),
    onSuccess: async (company) => {
      localStorage.removeItem(DRAFT_KEY);
      await queryClient.invalidateQueries({ queryKey: crmCompaniesQueryKeys.all });
      router.push(`/workspaces/crm/companies/${company.id}` as Route);
    },
  });

  const checkDuplicates = async () => {
    const legalName = form.getValues('legal_name');
    const domain = form.getValues('domain');
    const email = form.getValues('primary_email');
    if (!legalName && !domain && !email) return;
    const results = await fetchCrmCompanies({ search: legalName || domain || email, pageSize: 5 });
    if (results.items.length > 0) {
      setDuplicateWarning(t('form.duplicateWarning', { name: results.items[0]?.display_name ?? '' }));
    } else {
      setDuplicateWarning(null);
    }
  };

  const onSubmit = form.handleSubmit((values) => {
    const payload: Record<string, unknown> = {
      ...values,
      entity_type: values.entity_type || undefined,
      employee_count: values.employee_count,
    };
    createMutation.mutate(payload);
  });

  const showProfileSection = useMemo(() => Boolean(profileKey), [profileKey]);

  if (!canCreateCrm(user)) {
    return <ErrorState title={tCrm('accessDenied')} message={tCrm('accessDeniedHint')} />;
  }

  if (createMutation.isPending) {
    return <LoadingState label={tCommon('saving')} />;
  }

  return (
    <form className="crm-company-form" onSubmit={onSubmit}>
      <section className="crm-form-section">
        <h2>{t('form.sections.identity')}</h2>
        <Input {...form.register('display_name')} placeholder={t('form.displayName')} required />
        <Input {...form.register('legal_name')} placeholder={t('form.legalName')} onBlur={() => void checkDuplicates()} />
        <Input {...form.register('trade_name')} placeholder={t('form.tradeName')} />
        <select {...form.register('company_type')}>
          {CRM_COMPANY_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`companyTypes.${type}` as 'companyTypes.other')}
            </option>
          ))}
        </select>
        <Input {...form.register('industry')} placeholder={t('fields.industry')} />
      </section>

      <section className="crm-form-section">
        <h2>{t('form.sections.contact')}</h2>
        <Input {...form.register('primary_email')} placeholder={tCrm('fields.email')} onBlur={() => void checkDuplicates()} />
        <Input {...form.register('primary_phone')} placeholder={tCrm('fields.phone')} />
        <Input {...form.register('website')} placeholder={t('form.website')} />
        <Input {...form.register('domain')} placeholder={t('fields.domain')} onBlur={() => void checkDuplicates()} />
        <Input {...form.register('linkedin_url')} placeholder={t('form.linkedin')} />
      </section>

      <section className="crm-form-section">
        <h2>{t('form.sections.registration')}</h2>
        <Input {...form.register('registration_number')} placeholder={t('form.registrationNumber')} />
        <Input {...form.register('tax_id')} placeholder={t('form.taxId')} />
        <Input {...form.register('ein')} placeholder={t('form.ein')} />
      </section>

      {showProfileSection ? (
        <section className="crm-form-section">
          <h2>{t('form.sections.profile')}</h2>
          {profileKey === 'investment_profile' ? (
            <>
              <Input {...form.register('investment_profile.aum', { valueAsNumber: true })} placeholder={t('form.aum')} type="number" />
              <TextArea {...form.register('investment_profile.notes')} placeholder={t('form.profileNotes')} />
            </>
          ) : null}
          {profileKey === 'brokerage_profile' ? (
            <>
              <Input {...form.register('brokerage_profile.license_number')} placeholder={t('form.licenseNumber')} />
              <Input {...form.register('brokerage_profile.specialization')} placeholder={t('form.specialization')} />
            </>
          ) : null}
          {profileKey === 'lender_profile' ? (
            <>
              <Input {...form.register('lender_profile.lender_type')} placeholder={t('form.lenderType')} />
              <Input {...form.register('lender_profile.nmls_id')} placeholder={t('form.nmlsId')} />
            </>
          ) : null}
          {profileKey === 'vendor_profile' ? (
            <>
              <Input {...form.register('vendor_profile.vendor_category')} placeholder={t('form.vendorCategory')} />
              <Input {...form.register('vendor_profile.payment_terms')} placeholder={t('form.paymentTerms')} />
            </>
          ) : null}
          {profileKey === 'law_firm_profile' ? (
            <Input {...form.register('law_firm_profile.bar_number')} placeholder={t('form.barNumber')} />
          ) : null}
          {profileKey === 'property_management_profile' ? (
            <Input
              {...form.register('property_management_profile.units_managed', { valueAsNumber: true })}
              placeholder={t('form.unitsManaged')}
              type="number"
            />
          ) : null}
        </section>
      ) : null}

      <section className="crm-form-section">
        <h2>{t('form.sections.notes')}</h2>
        <TextArea {...form.register('description')} placeholder={t('form.description')} />
        <TextArea {...form.register('notes')} placeholder={t('form.notes')} />
      </section>

      {duplicateWarning ? <p className="crm-duplicate-warning">{duplicateWarning}</p> : null}

      <div className="crm-form-actions">
        <Link href={'/workspaces/crm/companies' as Route} className="ih-btn ih-btn--secondary">
          {tCommon('cancel')}
        </Link>
        <Button type="submit">{mode === 'create' ? t('actions.create') : tCommon('save')}</Button>
      </div>
    </form>
  );
}
