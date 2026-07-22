import type { CurrentUser } from '@/lib/api/auth';

/** Curated executive personas — mapped from system role codes (no fake roles). */
export type ExecPersona =
  | 'ceo'
  | 'cfo'
  | 'sales'
  | 'ir'
  | 'pm'
  | 'marketing'
  | 'ops'
  | 'admin';

export type G8SectionId =
  | 'priorities'
  | 'kpi'
  | 'finance'
  | 'pipeline'
  | 'projects'
  | 'marketing'
  | 'ai'
  | 'approvals'
  | 'upcoming'
  | 'activity'
  | 'quickActions';

export const ALL_G8_SECTIONS: G8SectionId[] = [
  'priorities',
  'kpi',
  'finance',
  'pipeline',
  'projects',
  'marketing',
  'ai',
  'approvals',
  'upcoming',
  'activity',
  'quickActions',
];

/** Default section order + emphasis weights per persona (higher = earlier). */
const PERSONA_SECTION_ORDER: Record<ExecPersona, G8SectionId[]> = {
  ceo: [
    'priorities',
    'kpi',
    'finance',
    'pipeline',
    'projects',
    'approvals',
    'ai',
    'marketing',
    'upcoming',
    'activity',
    'quickActions',
  ],
  cfo: [
    'priorities',
    'kpi',
    'finance',
    'approvals',
    'pipeline',
    'projects',
    'ai',
    'upcoming',
    'activity',
    'marketing',
    'quickActions',
  ],
  sales: [
    'priorities',
    'kpi',
    'pipeline',
    'upcoming',
    'activity',
    'ai',
    'approvals',
    'finance',
    'projects',
    'marketing',
    'quickActions',
  ],
  ir: [
    'priorities',
    'kpi',
    'pipeline',
    'finance',
    'approvals',
    'upcoming',
    'ai',
    'activity',
    'projects',
    'marketing',
    'quickActions',
  ],
  pm: [
    'priorities',
    'kpi',
    'projects',
    'upcoming',
    'approvals',
    'ai',
    'activity',
    'finance',
    'pipeline',
    'marketing',
    'quickActions',
  ],
  marketing: [
    'priorities',
    'kpi',
    'marketing',
    'pipeline',
    'ai',
    'activity',
    'upcoming',
    'approvals',
    'finance',
    'projects',
    'quickActions',
  ],
  ops: [
    'priorities',
    'kpi',
    'projects',
    'pipeline',
    'approvals',
    'upcoming',
    'activity',
    'ai',
    'finance',
    'marketing',
    'quickActions',
  ],
  admin: ALL_G8_SECTIONS,
};

const ROLE_TO_PERSONA: Array<{ codes: string[]; persona: ExecPersona }> = [
  { codes: ['super_admin'], persona: 'admin' },
  { codes: ['finance'], persona: 'cfo' },
  { codes: ['sales'], persona: 'sales' },
  { codes: ['investor_relations'], persona: 'ir' },
  { codes: ['construction'], persona: 'pm' },
  { codes: ['marketing'], persona: 'marketing' },
  { codes: ['operations'], persona: 'ops' },
  { codes: ['executive', 'partner'], persona: 'ceo' },
];

export function resolveExecPersona(user: CurrentUser | null | undefined): ExecPersona {
  if (!user?.roles?.length) return 'ceo';
  const codes = new Set(user.roles.map((r) => r.code));
  for (const mapping of ROLE_TO_PERSONA) {
    if (mapping.codes.some((c) => codes.has(c))) return mapping.persona;
  }
  return 'ceo';
}

export function defaultSectionsForPersona(persona: ExecPersona): G8SectionId[] {
  return PERSONA_SECTION_ORDER[persona] ?? ALL_G8_SECTIONS;
}

/** KPI ids allowed in the compact strip (curated). */
export type G8KpiId =
  | 'cash'
  | 'collections'
  | 'payments'
  | 'pipeline'
  | 'committed'
  | 'projects'
  | 'atRisk'
  | 'marketingSpend'
  | 'attributedRevenue'
  | 'criticalRisks';

export const DEFAULT_KPIS_BY_PERSONA: Record<ExecPersona, G8KpiId[]> = {
  ceo: ['cash', 'pipeline', 'committed', 'projects', 'atRisk', 'criticalRisks'],
  cfo: ['cash', 'collections', 'payments', 'committed', 'atRisk', 'criticalRisks'],
  sales: ['pipeline', 'collections', 'committed', 'criticalRisks', 'projects', 'cash'],
  ir: ['committed', 'pipeline', 'cash', 'collections', 'criticalRisks', 'projects'],
  pm: ['projects', 'atRisk', 'payments', 'cash', 'criticalRisks', 'pipeline'],
  marketing: ['marketingSpend', 'attributedRevenue', 'pipeline', 'criticalRisks', 'cash', 'projects'],
  ops: ['projects', 'atRisk', 'pipeline', 'payments', 'criticalRisks', 'cash'],
  admin: ['cash', 'pipeline', 'committed', 'projects', 'atRisk', 'criticalRisks'],
};
