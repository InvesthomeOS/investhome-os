'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  fetchDesignSourceRegions,
  fetchFurnitureItems,
  saveDesignVersion,
  type DesignParameters,
  type DesignProject,
  type DesignVersion,
  type FurnitureItem,
} from '@/lib/api/design';
import { drawingPreviewUrl } from '@/lib/api/drawing-intelligence';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

interface PlacedItem {
  instanceId: string;
  catalogId: string;
  x: number;
  y: number;
  rotation: number;
  width: number;
  depth: number;
  locked: boolean;
}

interface FurnitureLayoutProps {
  design: DesignProject;
  latestVersion: DesignVersion | null;
  onVersionSaved: () => void;
}

function furnitureShape(type: string): string {
  const shapes: Record<string, string> = {
    sofa: 'M4,20 L36,20 L36,12 L4,12 Z',
    bed: 'M2,18 L38,18 L38,8 L2,8 Z',
    dining_table: 'M2,14 L38,14 L38,10 L2,10 Z M6,14 L6,18 M34,14 L34,18',
    dining_chair: 'M12,18 L28,18 L28,10 L12,10 Z M14,18 L14,22 M26,18 L26,22',
    coffee_table: 'M6,16 L34,16 L34,12 L6,12 Z M10,16 L10,20 M30,16 L30,20',
    toilet: 'M14,8 L26,8 L26,18 L14,18 Z M16,18 L24,22 L16,22 Z',
    shower: 'M8,6 L32,6 L32,20 L8,20 Z M20,6 L20,20 M8,12 L32,12',
    kitchen_island: 'M4,10 L36,10 L36,18 L4,18 Z',
    rug: 'M2,22 L38,22 L38,2 L2,2 Z',
    default: 'M4,16 L36,16 L36,8 L4,8 Z',
  };
  return shapes[type] ?? shapes.default ?? 'M4,16 L36,16 L36,8 L4,8 Z';
}

function boxesOverlap(a: PlacedItem, b: PlacedItem): boolean {
  return !(
    a.x + a.width < b.x ||
    b.x + b.width < a.x ||
    a.y + a.depth < b.y ||
    b.y + b.depth < a.y
  );
}

export function FurnitureLayout({ design, latestVersion, onVersionSaved }: FurnitureLayoutProps) {
  const t = useTranslations('design.furnitureLayout');
  const tCommon = useTranslations('common');
  const { user } = useAuth();

  const [catalog, setCatalog] = useState<FurnitureItem[]>([]);
  const [placed, setPlaced] = useState<PlacedItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hasGeometry, setHasGeometry] = useState(false);
  const [history, setHistory] = useState<PlacedItem[][]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState<{ id: string; offsetX: number; offsetY: number } | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);
  const canSave = user ? hasPermission(user, 'design', 'save_version') : false;

  const pushHistory = useCallback((next: PlacedItem[]) => {
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), next]);
    setHistoryIndex((idx) => idx + 1);
    setPlaced(next);
  }, [historyIndex]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [furnitureRes, regionsRes] = await Promise.all([
        fetchFurnitureItems(),
        fetchDesignSourceRegions(design.id),
      ]);
      setCatalog(furnitureRes.items);
      setHasGeometry(regionsRes.mode === 'room_regions' && regionsRes.regions.some((r) => r.has_geometry));

      const params = latestVersion?.design_parameters;
      if (params?.furniture_placements?.length) {
        const items: PlacedItem[] = params.furniture_placements.map((placement) => {
          const catalogId = placement.catalog_id;
          const cat = furnitureRes.items.find((f) => f.id === catalogId);
          return {
            instanceId: placement.instance_id,
            catalogId,
            x: placement.x,
            y: placement.y,
            rotation: placement.rotation ?? 0,
            width: placement.width ?? cat?.width ?? 80,
            depth: placement.depth ?? cat?.depth ?? 60,
            locked: false,
          };
        });
        setPlaced(items);
        setHistory([items]);
        setHistoryIndex(0);
      } else if (params?.furniture_items?.length) {
        const items: PlacedItem[] = params.furniture_items.map((catalogId, index) => {
          const cat = furnitureRes.items.find((f) => f.id === catalogId);
          const instanceId = `${catalogId}-${index}`;
          const pos = params.furniture_positions?.[catalogId] ?? params.furniture_positions?.[instanceId] ?? { x: 50 + index * 30, y: 50 + index * 20 };
          return {
            instanceId,
            catalogId,
            x: pos.x,
            y: pos.y,
            rotation: params.furniture_rotations?.[catalogId] ?? params.furniture_rotations?.[instanceId] ?? 0,
            width: params.furniture_dimensions?.[catalogId]?.width ?? params.furniture_dimensions?.[instanceId]?.width ?? cat?.width ?? 80,
            depth: params.furniture_dimensions?.[catalogId]?.depth ?? params.furniture_dimensions?.[instanceId]?.depth ?? cat?.depth ?? 60,
            locked: false,
          };
        });
        setPlaced(items);
        setHistory([items]);
        setHistoryIndex(0);
      }
    } catch {
      setError(t('loadError'));
    }
  }, [design.id, latestVersion, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const catalogMap = useMemo(
    () => Object.fromEntries(catalog.map((item) => [item.id, item])),
    [catalog],
  );

  const overlaps = useMemo(() => {
    const warnings: string[] = [];
    for (let i = 0; i < placed.length; i++) {
      for (let j = i + 1; j < placed.length; j++) {
        const itemA = placed[i];
        const itemB = placed[j];
        if (!itemA || !itemB) continue;
        if (!itemA.locked && !itemB.locked && boxesOverlap(itemA, itemB)) {
          const a = catalogMap[itemA.catalogId]?.name ?? itemA.catalogId;
          const b = catalogMap[itemB.catalogId]?.name ?? itemB.catalogId;
          warnings.push(`${a} / ${b}`);
        }
      }
    }
    return warnings;
  }, [placed, catalogMap]);

  const handleAdd = (catalogId: string) => {
    const cat = catalogMap[catalogId];
    if (!cat) return;
    const next: PlacedItem = {
      instanceId: `${catalogId}-${Date.now()}`,
      catalogId,
      x: 80,
      y: 80,
      rotation: cat.default_rotation,
      width: cat.width ?? 80,
      depth: cat.depth ?? 60,
      locked: false,
    };
    pushHistory([...placed, next]);
    setSelectedId(next.instanceId);
  };

  const handleDelete = () => {
    if (!selectedId) return;
    pushHistory(placed.filter((item) => item.instanceId !== selectedId));
    setSelectedId(null);
  };

  const handleDuplicate = () => {
    const item = placed.find((p) => p.instanceId === selectedId);
    if (!item) return;
    const copy: PlacedItem = {
      ...item,
      instanceId: `${item.catalogId}-${Date.now()}`,
      x: item.x + 20,
      y: item.y + 20,
      locked: false,
    };
    pushHistory([...placed, copy]);
    setSelectedId(copy.instanceId);
  };

  const handleLockToggle = () => {
    if (!selectedId) return;
    pushHistory(
      placed.map((item) =>
        item.instanceId === selectedId ? { ...item, locked: !item.locked } : item,
      ),
    );
  };

  const handleRotate = (delta: number) => {
    if (!selectedId) return;
    pushHistory(
      placed.map((item) =>
        item.instanceId === selectedId
          ? { ...item, rotation: (item.rotation + delta) % 360 }
          : item,
      ),
    );
  };

  const handleUndo = () => {
    if (historyIndex <= 0) return;
    const prev = historyIndex - 1;
    setHistoryIndex(prev);
    setPlaced(history[prev] ?? []);
  };

  const handleRedo = () => {
    if (historyIndex >= history.length - 1) return;
    const next = historyIndex + 1;
    setHistoryIndex(next);
    setPlaced(history[next] ?? []);
  };

  const handleReset = () => {
    pushHistory([]);
    setSelectedId(null);
  };

  const handlePointerDown = (instanceId: string, event: React.PointerEvent) => {
    const item = placed.find((p) => p.instanceId === instanceId);
    if (!item || item.locked) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    setSelectedId(instanceId);
    setDragging({
      id: instanceId,
      offsetX: event.clientX - rect.left - item.x,
      offsetY: event.clientY - rect.top - item.y,
    });
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent) => {
    if (!dragging) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = Math.max(0, event.clientX - rect.left - dragging.offsetX);
    const y = Math.max(0, event.clientY - rect.top - dragging.offsetY);
    setPlaced((prev) =>
      prev.map((item) =>
        item.instanceId === dragging.id ? { ...item, x, y } : item,
      ),
    );
  };

  const handlePointerUp = () => {
    if (dragging) {
      pushHistory(placed);
      setDragging(null);
    }
  };

  const buildParameters = (): DesignParameters => {
    const base = latestVersion?.design_parameters ?? {
      mode: hasGeometry ? 'room_regions' : 'basic_overlay',
      palette: 'default',
      regions: [],
      backgroundColor: '#F5F0E8',
    };
    const furniturePlacements = placed.map((item) => ({
      instance_id: item.instanceId,
      catalog_id: item.catalogId,
      x: item.x,
      y: item.y,
      rotation: item.rotation,
      width: item.width,
      depth: item.depth,
      height: catalogMap[item.catalogId]?.height ?? 0,
    }));
    return {
      ...base,
      furniture_placements: furniturePlacements,
      furniture_items: placed.map((p) => p.catalogId),
      editor_metadata: { layout_mode: hasGeometry ? 'geometry_assisted' : 'free_layout' },
    };
  };

  const handleSave = async () => {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      await saveDesignVersion(design.id, buildParameters());
      onVersionSaved();
    } catch {
      setError(t('saveError'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="design-furniture-layout">
      <div className="design-furniture-layout__header">
        <div>
          <h3 className="leads-form__section-title">{t('title')}</h3>
          <p className="design-color-studio__mode-label">
            {hasGeometry ? t('modeGeometry') : t('modeFreeLayout')}
          </p>
        </div>
        <div className="design-color-studio__actions">
          <button type="button" className="leads__button leads__button--ghost" onClick={handleUndo} disabled={historyIndex <= 0}>
            {t('undo')}
          </button>
          <button type="button" className="leads__button leads__button--ghost" onClick={handleRedo} disabled={historyIndex >= history.length - 1}>
            {t('redo')}
          </button>
          <button type="button" className="leads__button leads__button--ghost" onClick={handleReset}>
            {t('reset')}
          </button>
          {canSave && (
            <button type="button" className="leads__button leads__button--primary" disabled={saving} onClick={() => void handleSave()}>
              {saving ? tCommon('loading') : t('saveVersion')}
            </button>
          )}
        </div>
      </div>

      <p className="design-furniture-layout__disclaimer">{t('disclaimer')}</p>
      {error && <p className="leads__state leads__state--error">{error}</p>}
      {overlaps.length > 0 && (
        <p className="leads__state leads__state--error">{t('overlapWarning', { items: overlaps.join(', ') })}</p>
      )}

      <div className="design-furniture-layout__layout">
        <aside className="design-furniture-layout__catalog">
          <h4>{t('catalog')}</h4>
          <ul className="design-furniture-layout__catalog-list">
            {catalog.map((item) => (
              <li key={item.id}>
                <button type="button" className="leads__button leads__button--secondary" onClick={() => handleAdd(item.id)}>
                  + {item.name}
                </button>
              </li>
            ))}
          </ul>
          {selectedId && (
            <div className="design-furniture-layout__selection-tools">
              <button type="button" className="leads__button leads__button--ghost" onClick={handleDuplicate}>{t('duplicate')}</button>
              <button type="button" className="leads__button leads__button--ghost" onClick={() => handleRotate(15)}>{t('rotate')}</button>
              <button type="button" className="leads__button leads__button--ghost" onClick={handleLockToggle}>{t('lock')}</button>
              <button type="button" className="leads__button leads__button--ghost" onClick={handleDelete}>{t('delete')}</button>
            </div>
          )}
        </aside>

        <div
          ref={canvasRef}
          className="design-furniture-layout__canvas"
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        >
          <iframe
            title={design.title}
            src={drawingPreviewUrl(design.document_id)}
            className="documents-preview__frame design-furniture-layout__plan"
          />
          {placed.map((item) => {
            const cat = catalogMap[item.catalogId];
            return (
              <div
                key={item.instanceId}
                className={`design-furniture-layout__item${selectedId === item.instanceId ? ' design-furniture-layout__item--selected' : ''}${item.locked ? ' design-furniture-layout__item--locked' : ''}`}
                style={{
                  left: item.x,
                  top: item.y,
                  width: item.width,
                  height: item.depth,
                  transform: `rotate(${item.rotation}deg)`,
                }}
                onPointerDown={(e) => handlePointerDown(item.instanceId, e)}
              >
                <svg viewBox="0 0 40 24" className="design-furniture-layout__shape">
                  <path d={furnitureShape(cat?.furniture_type ?? 'default')} fill="currentColor" opacity="0.7" />
                </svg>
                <span className="design-furniture-layout__label">{cat?.name ?? item.catalogId}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
