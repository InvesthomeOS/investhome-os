export const INVESTORS_MODULE_ID = 'investors' as const;

export interface InvestorsModuleManifest {
  id: typeof INVESTORS_MODULE_ID;
  name: string;
  description: string;
}

export const investorsModuleManifest: InvestorsModuleManifest = {
  id: INVESTORS_MODULE_ID,
  name: 'Investors',
  description: 'Capital partner relations, commitments, and investor communications.',
};
