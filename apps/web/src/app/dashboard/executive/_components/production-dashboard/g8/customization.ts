import {
  ALL_G8_SECTIONS,
  DEFAULT_KPIS_BY_PERSONA,
  defaultSectionsForPersona,
  type ExecPersona,
  type G8KpiId,
  type G8SectionId,
} from './role-views';

export const G8_LAYOUT_STORAGE_KEY = 'investhome.exec.g8.layout.v1';
export const G8_AI_TRIAGE_STORAGE_KEY = 'investhome.exec.g8.ai-triage.v1';

export type G8Density = 'compact' | 'standard';

export interface G8LayoutPrefs {
  personaOverride: ExecPersona | null;
  sections: G8SectionId[];
  hiddenSections: G8SectionId[];
  kpis: G8KpiId[];
  density: G8Density;
}

export interface G8AiTriageState {
  dismissed: string[];
  snoozedUntil: Record<string, string>;
  accepted: string[];
}

export function defaultLayoutForPersona(persona: ExecPersona): G8LayoutPrefs {
  return {
    personaOverride: null,
    sections: defaultSectionsForPersona(persona),
    hiddenSections: [],
    kpis: DEFAULT_KPIS_BY_PERSONA[persona],
    density: 'compact',
  };
}

export function loadLayoutPrefs(persona: ExecPersona): G8LayoutPrefs {
  if (typeof window === 'undefined') return defaultLayoutForPersona(persona);
  try {
    const raw = window.localStorage.getItem(G8_LAYOUT_STORAGE_KEY);
    if (!raw) return defaultLayoutForPersona(persona);
    const parsed = JSON.parse(raw) as Partial<G8LayoutPrefs>;
    const sections = Array.isArray(parsed.sections)
      ? parsed.sections.filter((s): s is G8SectionId => ALL_G8_SECTIONS.includes(s as G8SectionId))
      : defaultSectionsForPersona(persona);
    const hiddenSections = Array.isArray(parsed.hiddenSections)
      ? parsed.hiddenSections.filter((s): s is G8SectionId => ALL_G8_SECTIONS.includes(s as G8SectionId))
      : [];
    const kpis = Array.isArray(parsed.kpis)
      ? (parsed.kpis as G8KpiId[]).slice(0, 8)
      : DEFAULT_KPIS_BY_PERSONA[persona];
    return {
      personaOverride:
        parsed.personaOverride &&
        ['ceo', 'cfo', 'sales', 'ir', 'pm', 'marketing', 'ops', 'admin'].includes(
          parsed.personaOverride,
        )
          ? parsed.personaOverride
          : null,
      sections: sections.length ? sections : defaultSectionsForPersona(persona),
      hiddenSections,
      kpis: kpis.length ? kpis : DEFAULT_KPIS_BY_PERSONA[persona],
      density: parsed.density === 'standard' ? 'standard' : 'compact',
    };
  } catch {
    return defaultLayoutForPersona(persona);
  }
}

export function saveLayoutPrefs(prefs: G8LayoutPrefs): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(G8_LAYOUT_STORAGE_KEY, JSON.stringify(prefs));
}

export function loadAiTriage(): G8AiTriageState {
  if (typeof window === 'undefined') {
    return { dismissed: [], snoozedUntil: {}, accepted: [] };
  }
  try {
    const raw = window.localStorage.getItem(G8_AI_TRIAGE_STORAGE_KEY);
    if (!raw) return { dismissed: [], snoozedUntil: {}, accepted: [] };
    const parsed = JSON.parse(raw) as Partial<G8AiTriageState>;
    return {
      dismissed: Array.isArray(parsed.dismissed) ? parsed.dismissed : [],
      snoozedUntil:
        parsed.snoozedUntil && typeof parsed.snoozedUntil === 'object'
          ? parsed.snoozedUntil
          : {},
      accepted: Array.isArray(parsed.accepted) ? parsed.accepted : [],
    };
  } catch {
    return { dismissed: [], snoozedUntil: {}, accepted: [] };
  }
}

export function saveAiTriage(state: G8AiTriageState): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(G8_AI_TRIAGE_STORAGE_KEY, JSON.stringify(state));
}

export function visibleSections(prefs: G8LayoutPrefs): G8SectionId[] {
  const hidden = new Set(prefs.hiddenSections);
  return prefs.sections.filter((s) => !hidden.has(s));
}
