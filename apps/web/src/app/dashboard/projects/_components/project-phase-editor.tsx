'use client';

import { useEffect, useState } from 'react';
import { useLocale } from 'next-intl';

import {
  fetchProjectPhases,
  saveProjectPhases,
  type PhaseDraft,
} from '@/lib/api/project-phases';
import { fetchInventoryAssets, updateInventoryAsset, type InventoryAsset } from '@/lib/api/inventory';

type ProjectPhaseEditorProps = {
  projectId?: string | null;
  drafts?: PhaseDraft[];
  onChange?: (next: PhaseDraft[]) => void;
};

function move(rows: PhaseDraft[], index: number, direction: -1 | 1): PhaseDraft[] {
  const next = rows.slice();
  const target = index + direction;
  if (target < 0 || target >= next.length) return rows;
  const [row] = next.splice(index, 1);
  next.splice(target, 0, row);
  return next.map((item, order) => ({ ...item, display_order: order }));
}

export function ProjectPhaseEditor({ projectId, drafts, onChange }: ProjectPhaseEditorProps) {
  const locale = useLocale();
  const tr = locale === 'tr';
  const controlled = typeof onChange === 'function';
  const [rows, setRows] = useState<PhaseDraft[]>(drafts ?? []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (controlled) setRows(drafts ?? []);
  }, [controlled, drafts]);

  useEffect(() => {
    if (controlled || !projectId) return;
    let cancelled = false;
    setLoading(true);
    fetchProjectPhases(projectId, true)
      .then((items) => {
        if (cancelled) return;
        setRows(
          items.map((item) => ({
            id: item.id,
            name: item.name,
            display_order: item.display_order,
            active: item.active,
            address_line: item.address_line ?? '',
            unit_count: item.unit_count,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) setError(tr ? 'Fazlar yüklenemedi.' : 'Phases could not be loaded.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [controlled, projectId, tr]);

  const commit = async (next: PhaseDraft[], persist = !controlled) => {
    setRows(next);
    onChange?.(next);
    if (!persist || !projectId) return;
    setError(null);
    try {
      await saveProjectPhases(projectId, next);
      const fresh = await fetchProjectPhases(projectId, true);
      setRows(
        fresh.map((item) => ({
          id: item.id,
          name: item.name,
          display_order: item.display_order,
          active: item.active,
          address_line: item.address_line ?? '',
          unit_count: item.unit_count,
        })),
      );
    } catch {
      setError(tr ? 'Faz kaydedilemedi.' : 'Phase could not be saved.');
    }
  };

  const copy = {
    title: tr ? 'Fazlar' : 'Phases',
    empty: tr ? 'Bu projede faz yok.' : 'This project has no phases.',
    add: tr ? 'Faz ekle' : 'Add phase',
    name: tr ? 'Faz adı' : 'Phase name',
    address: tr ? 'Adres' : 'Address',
    active: tr ? 'Aktif' : 'Active',
    units: tr ? 'ünite' : 'units',
    up: tr ? 'Yukarı' : 'Up',
    down: tr ? 'Aşağı' : 'Down',
    remove: tr ? 'Kaldır' : 'Remove',
  };

  return (
    <section className="leads-form" data-testid="project-phases">
      <p className="leads-form__section-title">{copy.title}</p>
      {loading ? <p>{tr ? 'Yükleniyor…' : 'Loading…'}</p> : null}
      {!loading && rows.length === 0 ? <p data-testid="project-phases-empty">{copy.empty}</p> : null}
      {rows.map((row, index) => (
        <div key={row.id || `draft-${index}`} className="leads-form__grid" data-testid="project-phase-row">
          <label className="leads__field">
            <span>{copy.name}</span>
            <input
              value={row.name}
              onChange={(event) => {
                const next = rows.slice();
                next[index] = { ...row, name: event.target.value };
                void commit(next, false);
              }}
              onBlur={(event) => {
                const next = rows.slice();
                next[index] = { ...row, name: event.target.value };
                if (!controlled) void commit(next, true);
              }}
            />
          </label>
          <label className="leads__field">
            <span>{copy.address}</span>
            <input
              value={row.address_line ?? ''}
              onChange={(event) => {
                const next = rows.slice();
                next[index] = { ...row, address_line: event.target.value };
                void commit(next, false);
              }}
              onBlur={(event) => {
                const next = rows.slice();
                next[index] = { ...row, address_line: event.target.value };
                if (!controlled) void commit(next, true);
              }}
            />
          </label>
          <label className="leads__field">
            <span>{copy.active}</span>
            <input
              type="checkbox"
              checked={row.active}
              onChange={(event) => {
                const next = rows.slice();
                next[index] = { ...row, active: event.target.checked };
                void commit(next);
              }}
            />
          </label>
          {'unit_count' in row ? (
            <span>
              {String((row as PhaseDraft & { unit_count?: number }).unit_count ?? 0)} {copy.units}
            </span>
          ) : null}
          <button type="button" onClick={() => void commit(move(rows, index, -1))}>
            {copy.up}
          </button>
          <button type="button" onClick={() => void commit(move(rows, index, 1))}>
            {copy.down}
          </button>
          <button
            type="button"
            onClick={() => {
              if (!row.id) {
                void commit(rows.filter((_, item) => item !== index));
                return;
              }
              const next = rows.slice();
              next[index] = { ...row, active: false };
              void commit(next);
            }}
          >
            {copy.remove}
          </button>
        </div>
      ))}
      <button
        type="button"
        data-testid="project-phase-add"
        onClick={() =>
          void commit([...rows, { name: '', display_order: rows.length, active: true }])
        }
      >
        {copy.add}
      </button>
      {error ? <p className="leads__error">{error}</p> : null}
      {projectId && !controlled ? <PhaseUnitAssigner projectId={projectId} phases={rows} /> : null}
    </section>
  );
}

function PhaseUnitAssigner({ projectId, phases }: { projectId: string; phases: PhaseDraft[] }) {
  const locale = useLocale();
  const tr = locale === 'tr';
  const active = phases.filter((phase) => phase.active && phase.id);
  const [units, setUnits] = useState<InventoryAsset[]>([]);
  const [filter, setFilter] = useState('');
  const [phaseId, setPhaseId] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchInventoryAssets({ project_id: projectId, page_size: 100 })
      .then((result) => {
        if (!cancelled) setUnits(result.items);
      })
      .catch(() => {
        if (!cancelled) setMessage(tr ? 'Üniteler yüklenemedi.' : 'Units could not be loaded.');
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, tr]);

  if (!active.length) return null;
  const shown = units.filter((unit) => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return true;
    return unit.display_id.toLowerCase().includes(needle);
  });
  const phaseName = (id: string | null | undefined) => active.find((phase) => phase.id === id)?.name || '';

  const assign = async () => {
    if (!phaseId || selected.length === 0) return;
    setMessage(null);
    try {
      await Promise.all(selected.map((id) => updateInventoryAsset(id, { phase_id: phaseId })));
      const fresh = await fetchInventoryAssets({ project_id: projectId, page_size: 100 });
      setUnits(fresh.items);
      setSelected([]);
      setMessage(tr ? 'Faz atandı.' : 'Phase assigned.');
    } catch {
      setMessage(tr ? 'Faz atanamadı.' : 'Phase could not be assigned.');
    }
  };

  return (
    <div data-testid="phase-unit-assign">
      <div data-testid="project-phase-units">
        {phases.filter((phase) => phase.id).map((phase) => {
          const assigned = units.filter((unit) => unit.phase_id === phase.id);
          return (
            <div key={phase.id} data-testid="project-phase-unit-group">
              <strong>{phase.name}</strong>
              <span>{phase.active ? (tr ? 'Aktif' : 'Active') : (tr ? 'Pasif' : 'Inactive')}</span>
              <span>{phase.display_order}</span>
              <span>{assigned.length}</span>
              <ul>
                {assigned.map((unit) => (
                  <li key={unit.id}>{unit.display_id}</li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
      <p className="leads-form__section-title">{tr ? 'Ünite fazı' : 'Unit phase'}</p>
      <label className="leads__field">
        <span>{tr ? 'Ünite ara' : 'Filter units'}</span>
        <input value={filter} onChange={(event) => setFilter(event.target.value)} />
      </label>
      <ul>
        {shown.map((unit) => (
          <li key={unit.id}>
            <label>
              <input
                type="checkbox"
                checked={selected.includes(unit.id)}
                onChange={(event) =>
                  setSelected((current) =>
                    event.target.checked ? [...current, unit.id] : current.filter((id) => id !== unit.id),
                  )
                }
              />
              {unit.display_id}
              {phaseName(unit.phase_id) ? ` · ${phaseName(unit.phase_id)}` : ''}
            </label>
          </li>
        ))}
      </ul>
      <label className="leads__field">
        <span>{tr ? 'Faz' : 'Phase'}</span>
        <select value={phaseId} onChange={(event) => setPhaseId(event.target.value)}>
          <option value="">{tr ? 'Seçin' : 'Select'}</option>
          {active.map((phase) => (
            <option key={phase.id} value={phase.id}>
              {phase.name}
            </option>
          ))}
        </select>
      </label>
      <button type="button" data-testid="phase-unit-assign-save" disabled={!phaseId || selected.length === 0} onClick={() => void assign()}>
        {tr ? 'Seçilen ünitelere faz ata' : 'Assign phase to selected units'}
      </button>
      {message ? <p>{message}</p> : null}
    </div>
  );
}
