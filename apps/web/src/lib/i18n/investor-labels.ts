import { useTranslations } from 'next-intl';

import {
  ACCREDITATION_STATUSES,
  INVESTMENT_MODELS,
  INVESTOR_STATUSES,
  INVESTOR_TYPES,
  RISK_PROFILES,
  type AccreditationStatus,
  type InvestmentModel,
  type InvestorStatus,
  type InvestorType,
  type RiskProfile,
} from '@/lib/api/investors';

export function useInvestorLabels() {
  const tType = useTranslations('investors.types');
  const tStatus = useTranslations('investors.statuses');
  const tModel = useTranslations('investors.models');
  const tAccreditation = useTranslations('investors.accreditation');
  const tRisk = useTranslations('investors.riskProfiles');

  const getTypeLabel = (value: InvestorType | string): string => tType(value as InvestorType);
  const getStatusLabel = (value: InvestorStatus | string): string =>
    tStatus(value as InvestorStatus);
  const getModelLabel = (value: InvestmentModel | string | null | undefined): string => {
    if (!value) {
      return '—';
    }
    return tModel(value as InvestmentModel);
  };
  const getAccreditationLabel = (value: AccreditationStatus | string): string =>
    tAccreditation(value as AccreditationStatus);
  const getRiskLabel = (value: RiskProfile | string | null | undefined): string => {
    if (!value) {
      return '—';
    }
    return tRisk(value as RiskProfile);
  };

  const typeOptions = INVESTOR_TYPES.map((value) => ({ value, label: tType(value) }));
  const statusOptions = INVESTOR_STATUSES.map((value) => ({ value, label: tStatus(value) }));
  const modelOptions = INVESTMENT_MODELS.map((value) => ({ value, label: tModel(value) }));
  const accreditationOptions = ACCREDITATION_STATUSES.map((value) => ({
    value,
    label: tAccreditation(value),
  }));
  const riskOptions = RISK_PROFILES.map((value) => ({ value, label: tRisk(value) }));

  return {
    getTypeLabel,
    getStatusLabel,
    getModelLabel,
    getAccreditationLabel,
    getRiskLabel,
    typeOptions,
    statusOptions,
    modelOptions,
    accreditationOptions,
    riskOptions,
  };
}
