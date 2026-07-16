'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import type { InventoryPreference } from '@/lib/api/sales-inventory-matching';

interface InventorySearchCriteriaFormProps {
  preferences: InventoryPreference | null;
  canSave: boolean;
  searching: boolean;
  onSave: (values: Partial<InventoryPreference>) => Promise<void>;
  onSearch: (criteria: Record<string, unknown>) => Promise<void>;
}

export function InventorySearchCriteriaForm({
  preferences,
  canSave,
  searching,
  onSave,
  onSearch,
}: InventorySearchCriteriaFormProps) {
  const t = useTranslations('salesInventoryMatching');
  const [budgetMin, setBudgetMin] = useState(preferences?.budget_min ?? '');
  const [budgetMax, setBudgetMax] = useState(preferences?.budget_max ?? '');
  const [bedroomsMin, setBedroomsMin] = useState(preferences?.bedrooms_min?.toString() ?? '');
  const [search, setSearch] = useState('');

  return (
    <form
      className="leads-form leads-form--grid"
      onSubmit={(e) => {
        e.preventDefault();
        void onSearch({
          budget_min: budgetMin || undefined,
          budget_max: budgetMax || undefined,
          bedrooms_min: bedroomsMin ? Number(bedroomsMin) : undefined,
          search: search || undefined,
          availability_status: 'available',
        });
      }}
    >
      <label className="leads__field">
        <span>{t('fields.budgetMin')}</span>
        <input value={budgetMin} onChange={(e) => setBudgetMin(e.target.value)} />
      </label>
      <label className="leads__field">
        <span>{t('fields.budgetMax')}</span>
        <input value={budgetMax} onChange={(e) => setBudgetMax(e.target.value)} />
      </label>
      <label className="leads__field">
        <span>{t('fields.bedroomsMin')}</span>
        <input type="number" value={bedroomsMin} onChange={(e) => setBedroomsMin(e.target.value)} />
      </label>
      <label className="leads__field">
        <span>{t('fields.search')}</span>
        <input value={search} onChange={(e) => setSearch(e.target.value)} />
      </label>
      <div className="leads-form__actions">
        <Button type="submit" disabled={searching}>{searching ? t('actions.searching') : t('actions.search')}</Button>
        {canSave && (
          <Button
            type="button"
            variant="secondary"
            onClick={() =>
              void onSave({
                budget_min: budgetMin || null,
                budget_max: budgetMax || null,
                bedrooms_min: bedroomsMin ? Number(bedroomsMin) : null,
              } as Partial<InventoryPreference>)
            }
          >
            {t('actions.saveCriteria')}
          </Button>
        )}
      </div>
    </form>
  );
}
