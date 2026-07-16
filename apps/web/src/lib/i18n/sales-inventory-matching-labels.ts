'use client';

import { useTranslations } from 'next-intl';

const REJECTION_REASONS = [
  'budget',
  'size',
  'layout',
  'location',
  'floor',
  'exposure',
  'delivery_timing',
  'availability',
  'financing',
  'client_preference',
  'other',
] as const;

export function useSalesInventoryMatchingLabels() {
  const t = useTranslations('salesInventoryMatching');

  return {
    getAvailabilityLabel: (value: string) => t(`availability.${value}` as 'availability.available'),
    getRejectionReasonLabel: (value: string) => t(`rejectionReasons.${value}` as 'rejectionReasons.budget'),
    rejectionReasonOptions: REJECTION_REASONS.map((value) => ({
      value,
      label: t(`rejectionReasons.${value}` as 'rejectionReasons.budget'),
    })),
  };
}
