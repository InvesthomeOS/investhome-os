'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';

import { Button, ErrorState, Input, TextArea } from '@investhome/ui';

import { canCreateCrm } from '@/lib/crm/crm-permissions';
import { confirmDiscardUnsaved, saveFailedMessage } from '@/lib/crm/unsaved-form';
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
import '../companies/companies-ops.css';
import { useQueryClient } from '@tanstack/react-query';
import { fetchCrmCompanies } from '@/workspaces/crm/api/companies';

const DRAFT_KEY = 'investhome-crm-company-draft';

export function CrmCompanyForm() {
  const t = useTranslations('crm.companies');
  const tCrm = useTranslations('crm');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [saveError, setSaveError] = useState<string | null>(null);
  const router = useRouter();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { draftFormOpen } = useCrmCompaniesStore();
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);
  const [duplicateConfirmed, setDuplicateConfirmed] = useState(false);

  const form = useForm<CrmCompanyFormValues>({
    resolver: zodResolver(crmCompanyFormSchema) as never,
    defaultValues: crmCompanyFormDefaults,
  });

  const companyType = form.watch('company_type') as CrmCompanyType;
  const profileKey = PROFILE_TYPES_BY_COMPANY_TYPE[companyType];

  useEffect(() => {
    const saved = localStorage.getItem(DRAFT_KEY);
    if (saved && draftFormOpen) {
      try {
        form.reset(JSON.parse(saved) as CrmCompanyFormValues);
      } catch {
        localStorage.removeItem(DRAFT_KEY);
      }
    }
  }, [draftFormOpen, form]);

  useEffect(() => {
    const subscription = form.watch((values, info) => {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(values));
      if (
        info.name === 'display_name' ||
        info.name === 'legal_name' ||
        info.name === 'domain' ||
        info.name === 'primary_email'
      ) {
        setDuplicateConfirmed(false);
        setDuplicateWarning(null);
      }
    });
    return () => subscription.unsubscribe();
  }, [form]);

  const createMutation = useMutation({
    ...crmCompaniesMutations.create(),
    onSuccess: async (company) => {
      setSaveError(null);
      localStorage.removeItem(DRAFT_KEY);
      await queryClient.invalidateQueries({ queryKey: crmCompaniesQueryKeys.all });
      router.push(`/workspaces/crm/companies/${company.id}` as Route);
    },
    onError: () => {
      setSaveError(saveFailedMessage(!locale.startsWith('en')));
    },
  });

  const lookupDuplicate = async (): Promise<'found' | 'clear' | 'failed'> => {
    const legalName = form.getValues('legal_name');
    const domain = form.getValues('domain');
    const email = form.getValues('primary_email');
    const displayName = form.getValues('display_name');
    const search = legalName || domain || email || displayName;
    if (!search) {
      setDuplicateWarning(null);
      return 'clear';
    }
    try {
      const results = await fetchCrmCompanies({ search, pageSize: 5 });
      const match = results.items[0];
      if (match) {
        setDuplicateWarning(t('form.duplicateWarning', { name: match.display_name ?? '' }));
        setDuplicateConfirmed(false);
        return 'found';
      }
      setDuplicateWarning(null);
      return 'clear';
    } catch {
      setSaveError(t('form.duplicateCheckFailed'));
      return 'failed';
    }
  };

  const submitValues = (values: CrmCompanyFormValues) => {
    setSaveError(null);
    const payload: Record<string, unknown> = {
      ...values,
      entity_type: values.entity_type || undefined,
      employee_count: values.employee_count,
    };
    createMutation.mutate(payload);
  };

  const onSubmit = form.handleSubmit(async (values) => {
    if (!duplicateConfirmed) {
      const outcome = await lookupDuplicate();
      if (outcome !== 'clear') return;
    }
    submitValues(values);
  });

  const showProfileSection = useMemo(() => Boolean(profileKey), [profileKey]);

  if (!canCreateCrm(user)) {
    return <ErrorState title={tCrm('accessDenied')} message={tCrm('accessDeniedHint')} />;
  }

  return (
    <form className="crm-company-form" onSubmit={onSubmit}>
      <section className="crm-form-section">
        <h2>{t('form.sections.identity')}</h2>
        <Input label={t('form.displayName')} {...form.register('display_name')} placeholder={t('form.displayName')} required />
        <Input label={t('form.legalName')} {...form.register('legal_name')} placeholder={t('form.legalName')} />
        <Input label={t('form.tradeName')} {...form.register('trade_name')} placeholder={t('form.tradeName')} />
        <label className="ih-field">
          <span className="ih-field__label">{t('fields.companyType')}</span>
          <select className="ih-select" {...form.register('company_type')}>
            {CRM_COMPANY_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`companyTypes.${type}` as 'companyTypes.other')}
              </option>
            ))}
          </select>
        </label>
        <Input label={t('fields.industry')} {...form.register('industry')} placeholder={t('fields.industry')} />
      </section>

      <section className="crm-form-section">
        <h2>{t('form.sections.contact')}</h2>
        <Input label={tCrm('fields.email')} {...form.register('primary_email')} placeholder={tCrm('fields.email')} />
        <Input label={tCrm('fields.phone')} {...form.register('primary_phone')} placeholder={tCrm('fields.phone')} />
        <Input label={t('form.website')} {...form.register('website')} placeholder={t('form.website')} />
        <Input label={t('fields.domain')} {...form.register('domain')} placeholder={t('fields.domain')} />
        <Input label={t('form.linkedin')} {...form.register('linkedin_url')} placeholder={t('form.linkedin')} />
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

      {duplicateWarning ? (
        <div className="crm-duplicate-warning" role="status" data-testid="crm-company-duplicate">
          <p>{duplicateWarning}</p>
          <div className="crm-form-actions">
            <Button
              type="button"
              variant="secondary"
              data-testid="crm-company-duplicate-review"
              onClick={() => {
                setDuplicateWarning(null);
                setDuplicateConfirmed(false);
              }}
            >
              {t('form.duplicateReview')}
            </Button>
            <Button
              type="button"
              data-testid="crm-company-duplicate-continue"
              disabled={createMutation.isPending}
              onClick={() => {
                setDuplicateConfirmed(true);
                void form.handleSubmit((values) => submitValues(values))();
              }}
            >
              {t('form.duplicateContinue')}
            </Button>
          </div>
        </div>
      ) : null}
      {saveError ? (
        <p className="crm-company-form__error" role="alert" data-testid="crm-company-form-error">
          {saveError}
        </p>
      ) : null}

      <div className="crm-form-actions">
        <Link
          href={'/workspaces/crm/companies' as Route}
          className="ih-btn ih-btn--secondary"
          onClick={(event) => {
            if (form.formState.isDirty && !confirmDiscardUnsaved(!locale.startsWith('en'))) {
              event.preventDefault();
            }
          }}
        >
          {tCommon('cancel')}
        </Link>
        <Button type="submit" disabled={createMutation.isPending}>
          {createMutation.isPending ? tCommon('saving') : t('actions.create')}
        </Button>
      </div>
    </form>
  );
}
