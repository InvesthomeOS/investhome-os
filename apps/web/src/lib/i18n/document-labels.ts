import { useTranslations } from 'next-intl';

import {
  CONFIDENTIALITY_LEVELS,
  DOCUMENT_STATUSES,
  DOCUMENT_TYPES,
  type ConfidentialityLevel,
  type DocumentStatus,
  type DocumentType,
} from '@/lib/api/documents';

export function useDocumentLabels() {
  const t = useTranslations('documents');

  const getTypeLabel = (value: DocumentType | string | null | undefined) => {
    if (!value) return t('labels.unknown');
    const key = `types.${value}` as const;
    try {
      return t(key);
    } catch {
      return value;
    }
  };

  const getStatusLabel = (value: DocumentStatus | string | null | undefined) => {
    if (!value) return t('labels.unknown');
    return t(`statuses.${value}` as `statuses.${DocumentStatus}`);
  };

  const getConfidentialityLabel = (value: ConfidentialityLevel | string | null | undefined) => {
    if (!value) return t('labels.unknown');
    return t(`confidentiality.${value}` as `confidentiality.${ConfidentialityLevel}`);
  };

  return {
    getTypeLabel,
    getStatusLabel,
    getConfidentialityLabel,
    typeOptions: DOCUMENT_TYPES.map((value) => ({ value, label: getTypeLabel(value) })),
    statusOptions: DOCUMENT_STATUSES.map((value) => ({ value, label: getStatusLabel(value) })),
    confidentialityOptions: CONFIDENTIALITY_LEVELS.map((value) => ({
      value,
      label: getConfidentialityLabel(value),
    })),
  };
}
