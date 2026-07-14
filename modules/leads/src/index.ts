export const LEADS_MODULE_ID = 'leads' as const;

export interface LeadsModuleManifest {
  id: typeof LEADS_MODULE_ID;
  name: string;
  description: string;
}

export const leadsModuleManifest: LeadsModuleManifest = {
  id: LEADS_MODULE_ID,
  name: 'Leads',
  description: 'Acquisition pipeline, lead scoring, and funnel analytics.',
};
