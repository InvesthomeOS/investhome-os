'use client';

import { useTranslations } from 'next-intl';

import {
  CASH_OR_FINANCING,
  FOLLOW_UP_TYPES,
  INVESTMENT_OBJECTIVES,
  LEAD_INTEREST_TYPES,
  PURCHASE_TIMELINES,
  QUALIFICATION_STATUSES,
  RISK_TOLERANCES,
  type CashOrFinancing,
  type FollowUpType,
  type InvestmentObjective,
  type LeadInterestType,
  type PurchaseTimeline,
  type QualificationStatus,
  type RiskTolerance,
} from '@/lib/api/lead-qualification';

function labelKey(prefix: string, value: string): string {
  return `${prefix}.${value}`;
}

export function useLeadQualificationLabels() {
  const t = useTranslations('leadQualification');

  const getQualificationStatusLabel = (status: QualificationStatus | string | null) => {
    if (!status) return '—';
    const key = status.toLowerCase().replace(/ /g, '_') as QualificationStatus;
    return t.has(labelKey('statuses', key)) ? t(labelKey('statuses', key)) : status;
  };

  const getInvestmentObjectiveLabel = (value: InvestmentObjective | string | null) => {
    if (!value) return '—';
    return t.has(labelKey('objectives', value)) ? t(labelKey('objectives', value)) : value;
  };

  const getCashOrFinancingLabel = (value: CashOrFinancing | string | null) => {
    if (!value) return '—';
    return t.has(labelKey('financing', value)) ? t(labelKey('financing', value)) : value;
  };

  const getTimelineLabel = (value: PurchaseTimeline | string | null) => {
    if (!value) return '—';
    return t.has(labelKey('timelines', value)) ? t(labelKey('timelines', value)) : value;
  };

  const getRiskToleranceLabel = (value: RiskTolerance | string | null) => {
    if (!value) return '—';
    return t.has(labelKey('risk', value)) ? t(labelKey('risk', value)) : value;
  };

  const getInterestTypeLabel = (value: LeadInterestType | string) => {
    return t.has(labelKey('interestTypes', value)) ? t(labelKey('interestTypes', value)) : value;
  };

  const getFollowUpTypeLabel = (value: FollowUpType | string) => {
    return t.has(labelKey('followUpTypes', value)) ? t(labelKey('followUpTypes', value)) : value;
  };

  const getScoreComponentLabel = (key: string) => {
    return t.has(labelKey('scoreComponents', key)) ? t(labelKey('scoreComponents', key)) : key;
  };

  return {
    getQualificationStatusLabel,
    getInvestmentObjectiveLabel,
    getCashOrFinancingLabel,
    getTimelineLabel,
    getRiskToleranceLabel,
    getInterestTypeLabel,
    getFollowUpTypeLabel,
    getScoreComponentLabel,
    qualificationStatusOptions: QUALIFICATION_STATUSES.map((s) => ({
      value: s,
      label: t(labelKey('statuses', s)),
    })),
    investmentObjectiveOptions: INVESTMENT_OBJECTIVES.map((v) => ({
      value: v,
      label: t(labelKey('objectives', v)),
    })),
    cashOrFinancingOptions: CASH_OR_FINANCING.map((v) => ({
      value: v,
      label: t(labelKey('financing', v)),
    })),
    timelineOptions: PURCHASE_TIMELINES.map((v) => ({
      value: v,
      label: t(labelKey('timelines', v)),
    })),
    riskToleranceOptions: RISK_TOLERANCES.map((v) => ({
      value: v,
      label: t(labelKey('risk', v)),
    })),
    interestTypeOptions: LEAD_INTEREST_TYPES.map((v) => ({
      value: v,
      label: t(labelKey('interestTypes', v)),
    })),
    followUpTypeOptions: FOLLOW_UP_TYPES.map((v) => ({
      value: v,
      label: t(labelKey('followUpTypes', v)),
    })),
  };
}
