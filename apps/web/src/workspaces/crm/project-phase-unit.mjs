/** Project → optional phase → unit. The unit identifier stays a separate string. */

export function phaseFieldVisible(phases) {
  return Array.isArray(phases) && phases.some((phase) => phase && phase.id && phase.name);
}

export function unitsForPhase(units, phaseId, phases) {
  const rows = Array.isArray(units) ? units : [];
  if (!phaseFieldVisible(phases)) return rows;
  if (!phaseId) return [];
  return rows.filter((unit) => String(unit.phase_id || '') === String(phaseId));
}

export function interestLabel(project, phase, unit) {
  return [project, phase, unit].filter((part) => part && String(part).trim()).join(' · ');
}

export function unitIdentifier(value) {
  return String(value ?? '').trim();
}

export function unitSelectionLabel(unit) {
  const identifier = unitIdentifier(unit?.unit_number || unit?.label);
  const phase = String(unit?.phase_name || '').trim();
  if (phase && identifier && !identifier.startsWith(`${phase} `) && identifier !== phase) {
    return `${phase} · ${identifier}`;
  }
  return identifier;
}
