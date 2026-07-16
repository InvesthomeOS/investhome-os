import { useTranslations } from 'next-intl';

import {
  OPPORTUNITY_LOSS_REASONS,
  OPPORTUNITY_NEXT_ACTIONS,
  OPPORTUNITY_PARTY_TYPES,
  OPPORTUNITY_PRIORITIES,
  OPPORTUNITY_STAGES,
  type OpportunityLossReason,
  type OpportunityNextAction,
  type OpportunityPartyType,
  type OpportunityPriority,
  type OpportunityStage,
} from '@/lib/api/sales';

export function useSalesLabels() {
  const tStages = useTranslations('sales.stages');
  const tNextActions = useTranslations('sales.nextActions');
  const tLossReasons = useTranslations('sales.lossReasons');
  const tPartyTypes = useTranslations('sales.partyTypes');
  const tPriorities = useTranslations('sales.priorities');
  const tErrors = useTranslations('sales.errors');

  const getStageLabel = (value: OpportunityStage | string) =>
    tStages(value as OpportunityStage);
  const getNextActionLabel = (value: OpportunityNextAction | string) =>
    tNextActions(value as OpportunityNextAction);
  const getLossReasonLabel = (value: OpportunityLossReason | string) =>
    tLossReasons(value as OpportunityLossReason);
  const getPartyTypeLabel = (value: OpportunityPartyType | string) =>
    tPartyTypes(value as OpportunityPartyType);
  const getPriorityLabel = (value: OpportunityPriority | string) =>
    tPriorities(value as OpportunityPriority);

  const stageOptions = OPPORTUNITY_STAGES.map((stage) => ({
    value: stage,
    label: tStages(stage),
  }));

  const nextActionOptions = OPPORTUNITY_NEXT_ACTIONS.map((action) => ({
    value: action,
    label: tNextActions(action),
  }));

  const lossReasonOptions = OPPORTUNITY_LOSS_REASONS.map((reason) => ({
    value: reason,
    label: tLossReasons(reason),
  }));

  const partyTypeOptions = OPPORTUNITY_PARTY_TYPES.map((type) => ({
    value: type,
    label: tPartyTypes(type),
  }));

  const priorityOptions = OPPORTUNITY_PRIORITIES.map((priority) => ({
    value: priority,
    label: tPriorities(priority),
  }));

  const getErrorMessage = (errorKey: string | undefined, fallback: string) => {
    if (!errorKey) return fallback;
    const key = errorKey.startsWith('sales.errors.')
      ? errorKey.slice('sales.errors.'.length)
      : errorKey;
    if (OPPORTUNITY_STAGES.includes(key as OpportunityStage)) return fallback;
    try {
      return tErrors(key as never);
    } catch {
      return fallback;
    }
  };

  return {
    getStageLabel,
    getNextActionLabel,
    getLossReasonLabel,
    getPartyTypeLabel,
    getPriorityLabel,
    stageOptions,
    nextActionOptions,
    lossReasonOptions,
    partyTypeOptions,
    priorityOptions,
    getErrorMessage,
  };
}
