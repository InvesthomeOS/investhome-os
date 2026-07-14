export const EXECUTIVE_MODULE_ID = 'executive' as const;

export interface ExecutiveModuleManifest {
  id: typeof EXECUTIVE_MODULE_ID;
  name: string;
  description: string;
}

export const executiveModuleManifest: ExecutiveModuleManifest = {
  id: EXECUTIVE_MODULE_ID,
  name: 'Executive',
  description: 'Strategic oversight, KPIs, and portfolio intelligence.',
};
