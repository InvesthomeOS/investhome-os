export const FINANCE_MODULE_ID = 'finance' as const;

export interface FinanceModuleManifest {
  id: typeof FINANCE_MODULE_ID;
  name: string;
  description: string;
}

export const financeModuleManifest: FinanceModuleManifest = {
  id: FINANCE_MODULE_ID,
  name: 'Finance',
  description: 'Treasury operations, financial reporting, and compliance posture.',
};
