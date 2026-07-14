export const PROJECTS_MODULE_ID = 'projects' as const;

export interface ProjectsModuleManifest {
  id: typeof PROJECTS_MODULE_ID;
  name: string;
  description: string;
}

export const projectsModuleManifest: ProjectsModuleManifest = {
  id: PROJECTS_MODULE_ID,
  name: 'Projects',
  description: 'Development lifecycle, milestones, and delivery tracking.',
};
