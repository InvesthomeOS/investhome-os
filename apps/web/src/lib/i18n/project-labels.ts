import { useTranslations } from 'next-intl';

import {
  DEVELOPMENT_STAGES,
  DEVELOPMENT_TYPES,
  PROJECT_PRIORITIES,
  PROJECT_STATUSES,
  PROJECT_TEAM_ROLES,
  PROJECT_TYPES,
  type DevelopmentStage,
  type DevelopmentType,
  type ProjectPriority,
  type ProjectStatus,
  type ProjectTeamRole,
  type ProjectType,
} from '@/lib/api/projects';

export function useProjectLabels() {
  const tType = useTranslations('projects.types');
  const tDev = useTranslations('projects.developmentTypes');
  const tStatus = useTranslations('projects.statuses');
  const tPriority = useTranslations('projects.priorities');
  const tStage = useTranslations('projects.stages');
  const tRole = useTranslations('projects.teamRoles');

  const getTypeLabel = (value: ProjectType | string): string => tType(value as ProjectType);
  const getDevelopmentTypeLabel = (value: DevelopmentType | string): string =>
    tDev(value as DevelopmentType);
  const getStatusLabel = (value: ProjectStatus | string): string =>
    tStatus(value as ProjectStatus);
  const getPriorityLabel = (value: ProjectPriority | string): string =>
    tPriority(value as ProjectPriority);
  const getStageLabel = (value: DevelopmentStage | string): string =>
    tStage(value as DevelopmentStage);
  const getTeamRoleLabel = (value: ProjectTeamRole | string): string =>
    tRole(value as ProjectTeamRole);

  return {
    getTypeLabel,
    getDevelopmentTypeLabel,
    getStatusLabel,
    getPriorityLabel,
    getStageLabel,
    getTeamRoleLabel,
    typeOptions: PROJECT_TYPES.map((value) => ({ value, label: tType(value) })),
    developmentTypeOptions: DEVELOPMENT_TYPES.map((value) => ({
      value,
      label: tDev(value),
    })),
    statusOptions: PROJECT_STATUSES.map((value) => ({ value, label: tStatus(value) })),
    priorityOptions: PROJECT_PRIORITIES.map((value) => ({ value, label: tPriority(value) })),
    stageOptions: DEVELOPMENT_STAGES.map((value) => ({ value, label: tStage(value) })),
    teamRoleOptions: PROJECT_TEAM_ROLES.map((value) => ({ value, label: tRole(value) })),
  };
}
