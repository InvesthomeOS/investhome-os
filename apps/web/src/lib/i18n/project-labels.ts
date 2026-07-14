import { useTranslations } from 'next-intl';

import {
  DEVELOPMENT_TYPES,
  PROJECT_STATUSES,
  PROJECT_TYPES,
  type DevelopmentType,
  type ProjectStatus,
  type ProjectType,
} from '@/lib/api/projects';

export function useProjectLabels() {
  const tType = useTranslations('projects.types');
  const tDev = useTranslations('projects.developmentTypes');
  const tStatus = useTranslations('projects.statuses');

  const getTypeLabel = (value: ProjectType | string): string => tType(value as ProjectType);
  const getDevelopmentTypeLabel = (value: DevelopmentType | string): string =>
    tDev(value as DevelopmentType);
  const getStatusLabel = (value: ProjectStatus | string): string =>
    tStatus(value as ProjectStatus);

  const typeOptions = PROJECT_TYPES.map((value) => ({ value, label: tType(value) }));
  const developmentTypeOptions = DEVELOPMENT_TYPES.map((value) => ({
    value,
    label: tDev(value),
  }));
  const statusOptions = PROJECT_STATUSES.map((value) => ({ value, label: tStatus(value) }));

  return {
    getTypeLabel,
    getDevelopmentTypeLabel,
    getStatusLabel,
    typeOptions,
    developmentTypeOptions,
    statusOptions,
  };
}
