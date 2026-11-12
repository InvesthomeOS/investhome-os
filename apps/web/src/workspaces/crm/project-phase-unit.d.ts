export function phaseFieldVisible(
  phases: Array<{ id?: string; name?: string }> | null | undefined,
): boolean;
export function unitsForPhase<T extends { phase_id?: string }>(
  units: T[] | null | undefined,
  phaseId: string | null | undefined,
  phases: Array<{ id?: string; name?: string }> | null | undefined,
): T[];
export function interestLabel(
  project: string | null | undefined,
  phase: string | null | undefined,
  unit: string | null | undefined,
): string;
export function unitIdentifier(value: unknown): string;
export function unitSelectionLabel(unit: {
  unit_number?: string;
  label?: string;
  phase_name?: string;
} | null | undefined): string;
