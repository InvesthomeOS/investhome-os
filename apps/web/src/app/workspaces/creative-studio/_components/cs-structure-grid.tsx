'use client';

import type { DragEvent, KeyboardEvent, ReactNode } from 'react';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import './creative-studio-structure-grid.css';

export type CsStructureGridItem = {
  id: string;
  label: string;
  icon?: IhIconName;
  selected?: boolean;
  dragging?: boolean;
  dropTarget?: boolean;
  muted?: boolean;
  /** When set, replaces the label text (e.g. inline rename input). */
  labelNode?: ReactNode;
  onSelect: () => void;
  onDoubleClick?: () => void;
  onDragStart?: (e: DragEvent) => void;
  onDragOver?: (e: DragEvent) => void;
  onDrop?: (e: DragEvent) => void;
  onDragEnd?: () => void;
  testId?: string;
};

export type CsStructureGridProps = {
  items: CsStructureGridItem[];
  /** Optional trailing “add” card. */
  addLabel?: string;
  onAdd?: () => void;
  addTestId?: string;
  className?: string;
  testId?: string;
  ariaLabel?: string;
};

/**
 * Shared Creative Studio page-structure card grid.
 * Wrapping flex — no horizontal scrollbar. Used above CsBottomActionToolbar.
 */
export function CsStructureGrid({
  items,
  addLabel,
  onAdd,
  addTestId = 'cs-structure-grid-add',
  className,
  testId = 'cs-structure-grid',
  ariaLabel,
}: CsStructureGridProps) {
  const rootClass = ['cs-structure-grid', className].filter(Boolean).join(' ');

  function onKeyActivate(e: KeyboardEvent, action: () => void) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  }

  return (
    <ul className={rootClass} data-testid={testId} aria-label={ariaLabel} role="list">
      {items.map((item) => {
        const itemClass = [
          'cs-structure-grid__item',
          item.selected ? 'is-active' : '',
          item.dropTarget ? 'is-drop' : '',
          item.dragging ? 'is-dragging' : '',
          item.muted ? 'is-muted' : '',
        ]
          .filter(Boolean)
          .join(' ');

        return (
          <li key={item.id}>
            <div
              className={itemClass}
              draggable={Boolean(item.onDragStart)}
              data-testid={item.testId ?? `cs-structure-grid-item-${item.id}`}
              role="button"
              tabIndex={0}
              aria-pressed={item.selected || undefined}
              aria-label={item.label}
              onClick={item.onSelect}
              onDoubleClick={item.onDoubleClick}
              onKeyDown={(e) => onKeyActivate(e, item.onSelect)}
              onDragStart={item.onDragStart}
              onDragOver={item.onDragOver}
              onDrop={item.onDrop}
              onDragEnd={item.onDragEnd}
            >
              <span className="cs-structure-grid__icon" aria-hidden="true">
                {item.icon ? <IhIcon name={item.icon} size={16} /> : <span>⋯</span>}
              </span>
              <span className="cs-structure-grid__label">
                {item.labelNode ?? item.label}
              </span>
            </div>
          </li>
        );
      })}

      {onAdd ? (
        <li>
          <button
            type="button"
            className="cs-structure-grid__item is-add"
            data-testid={addTestId}
            aria-label={addLabel ?? 'Add'}
            onClick={onAdd}
          >
            <span className="cs-structure-grid__icon" aria-hidden="true">
              <IhIcon name="plus" size={18} />
            </span>
            {addLabel ? <span className="cs-structure-grid__label">{addLabel}</span> : null}
          </button>
        </li>
      ) : null}
    </ul>
  );
}
