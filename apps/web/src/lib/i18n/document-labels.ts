import { useTranslations } from 'next-intl';

import {
  CONFIDENTIALITY_LEVELS,
  DOCUMENT_FILE_KINDS,
  DOCUMENT_FOLDERS,
  DOCUMENT_STATUSES,
  DOCUMENT_TYPES,
  DOCUMENT_VISIBILITIES,
  type ConfidentialityLevel,
  type DocumentFileKind,
  type DocumentFolder,
  type DocumentStatus,
  type DocumentType,
  type DocumentVisibility,
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

  const getFileKindLabel = (value: DocumentFileKind | string | null | undefined) => {
    if (!value) return t('labels.unknown');
    try {
      return t(`fileKinds.${value}` as `fileKinds.${DocumentFileKind}`);
    } catch {
      return value;
    }
  };

  const getFolderLabel = (value: DocumentFolder | string | null | undefined) => {
    if (!value) return t('labels.unknown');
    try {
      return t(`folders.${value}` as `folders.${DocumentFolder}`);
    } catch {
      return value;
    }
  };

  const getVisibilityLabel = (value: DocumentVisibility | string | null | undefined) => {
    if (!value) return t('labels.unknown');
    try {
      return t(`visibility.${value}` as `visibility.${DocumentVisibility}`);
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
    getFileKindLabel,
    getFolderLabel,
    getVisibilityLabel,
    getStatusLabel,
    getConfidentialityLabel,
    typeOptions: DOCUMENT_TYPES.map((value) => ({ value, label: getTypeLabel(value) })),
    fileKindOptions: DOCUMENT_FILE_KINDS.map((value) => ({ value, label: getFileKindLabel(value) })),
    folderOptions: DOCUMENT_FOLDERS.map((value) => ({ value, label: getFolderLabel(value) })),
    visibilityOptions: DOCUMENT_VISIBILITIES.map((value) => ({
      value,
      label: getVisibilityLabel(value),
    })),
    statusOptions: DOCUMENT_STATUSES.map((value) => ({ value, label: getStatusLabel(value) })),
    confidentialityOptions: CONFIDENTIALITY_LEVELS.map((value) => ({
      value,
      label: getConfidentialityLabel(value),
    })),
  };
}
