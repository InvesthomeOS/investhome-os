import { MODULE_NAMES, type ModuleName } from '@investhome/shared';

export interface ModuleSection {
  title: string;
  description: string;
}

export const MODULE_SECTIONS: Record<ModuleName, ModuleSection> = {
  executive: {
    title: 'Executive',
    description: 'Strategic overview and portfolio intelligence.',
  },
  leads: {
    title: 'Leads',
    description: 'Pipeline visibility and acquisition funnel metrics.',
  },
  investors: {
    title: 'Investors',
    description: 'Capital partners, commitments, and relations.',
  },
  projects: {
    title: 'Projects',
    description: 'Development lifecycle and delivery tracking.',
  },
  finance: {
    title: 'Finance',
    description: 'Treasury, reporting, and compliance posture.',
  },
};

export function isModuleName(value: string): value is ModuleName {
  return (MODULE_NAMES as readonly string[]).includes(value);
}
