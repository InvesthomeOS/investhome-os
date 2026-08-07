'use client';

import { useMemo, useState } from 'react';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  filterTagSuggestions,
  normalizeTag,
  uniqueTags,
} from './media-library-tag-utils';

export type MediaLibraryTagEditorLabels = {
  searchPlaceholder: string;
  createLabel: string;
  createWithName: (name: string) => string;
  selectedLabel: string;
  suggestionsLabel: string;
  recentLabel: string;
  emptySuggestions: string;
  removeTag: string;
  apply: string;
  cancel: string;
  applying: string;
};

export type MediaLibraryTagEditorProps = {
  value: string[];
  libraryTags: string[];
  recentTags?: string[];
  labels: MediaLibraryTagEditorLabels;
  disabled?: boolean;
  busy?: boolean;
  error?: string | null;
  onChange: (tags: string[]) => void;
  onApply: () => void;
  onCancel: () => void;
  testIdPrefix?: string;
};

/**
 * Shared tag chip / search / create editor for quick-tag, detail, and bulk dialogs.
 */
export function MediaLibraryTagEditor({
  value,
  libraryTags,
  recentTags = [],
  labels,
  disabled = false,
  busy = false,
  error = null,
  onChange,
  onApply,
  onCancel,
  testIdPrefix = 'ml-tag-editor',
}: MediaLibraryTagEditorProps) {
  const [query, setQuery] = useState('');

  const selected = useMemo(() => uniqueTags(value), [value]);
  const selectedLower = useMemo(
    () => new Set(selected.map((t) => t.toLowerCase())),
    [selected],
  );

  const suggestions = useMemo(() => {
    const pool = uniqueTags([...libraryTags, ...recentTags]);
    return filterTagSuggestions(pool, query, selected);
  }, [libraryTags, recentTags, query, selected]);

  const recentVisible = useMemo(() => {
    return recentTags.filter((tag) => !selectedLower.has(tag.toLowerCase())).slice(0, 8);
  }, [recentTags, selectedLower]);

  const createCandidate = normalizeTag(query);
  const canCreate =
    Boolean(createCandidate) &&
    !selectedLower.has(createCandidate.toLowerCase()) &&
    !libraryTags.some((t) => t.toLowerCase() === createCandidate.toLowerCase());

  function toggleTag(tag: string) {
    if (disabled || busy) return;
    const normalized = normalizeTag(tag);
    if (!normalized) return;
    const key = normalized.toLowerCase();
    if (selectedLower.has(key)) {
      onChange(selected.filter((t) => t.toLowerCase() !== key));
      return;
    }
    onChange(uniqueTags([...selected, normalized]));
  }

  function createTag() {
    if (!canCreate) return;
    onChange(uniqueTags([...selected, createCandidate]));
    setQuery('');
  }

  return (
    <div className="ml-tag-editor" data-testid={testIdPrefix}>
      <label className="ml-tag-editor__search">
        <IhIcon name="search" size={12} />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              if (canCreate) createTag();
              else if (suggestions[0]) toggleTag(suggestions[0]);
            }
          }}
          placeholder={labels.searchPlaceholder}
          disabled={disabled || busy}
          data-testid={`${testIdPrefix}-search`}
        />
      </label>

      {selected.length ? (
        <div className="ml-tag-editor__section">
          <p className="ml-tag-editor__label">{labels.selectedLabel}</p>
          <div className="ml-tag-editor__chips">
            {selected.map((tag) => (
              <button
                key={tag}
                type="button"
                className="ml-tag-editor__chip-btn is-selected"
                onClick={() => toggleTag(tag)}
                disabled={disabled || busy}
                title={labels.removeTag}
                data-testid={`${testIdPrefix}-selected-${tag}`}
              >
                <StatusChip tone="info">{tag}</StatusChip>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {recentVisible.length && !query.trim() ? (
        <div className="ml-tag-editor__section">
          <p className="ml-tag-editor__label">{labels.recentLabel}</p>
          <div className="ml-tag-editor__chips">
            {recentVisible.map((tag) => (
              <button
                key={tag}
                type="button"
                className="ml-tag-editor__chip-btn"
                onClick={() => toggleTag(tag)}
                disabled={disabled || busy}
                data-testid={`${testIdPrefix}-recent-${tag}`}
              >
                <StatusChip tone="default">{tag}</StatusChip>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="ml-tag-editor__section">
        <p className="ml-tag-editor__label">{labels.suggestionsLabel}</p>
        <div className="ml-tag-editor__chips">
          {canCreate ? (
            <button
              type="button"
              className="ml-tag-editor__create"
              onClick={createTag}
              disabled={disabled || busy}
              data-testid={`${testIdPrefix}-create`}
            >
              <IhIcon name="plus" size={11} />
              {labels.createWithName(createCandidate)}
            </button>
          ) : null}
          {suggestions.length === 0 && !canCreate ? (
            <p className="ml-tag-editor__empty">{labels.emptySuggestions}</p>
          ) : (
            suggestions.slice(0, 24).map((tag) => (
              <button
                key={tag}
                type="button"
                className="ml-tag-editor__chip-btn"
                onClick={() => toggleTag(tag)}
                disabled={disabled || busy}
                data-testid={`${testIdPrefix}-suggest-${tag}`}
              >
                <StatusChip tone="default">{tag}</StatusChip>
              </button>
            ))
          )}
        </div>
      </div>

      {error ? (
        <p className="ml-tag-editor__error" role="alert" data-testid={`${testIdPrefix}-error`}>
          {error}
        </p>
      ) : null}

      <div className="ml-tag-editor__actions">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onCancel}
          disabled={busy}
          data-testid={`${testIdPrefix}-cancel`}
        >
          {labels.cancel}
        </Button>
        <Button
          type="button"
          variant="primary"
          size="sm"
          onClick={onApply}
          disabled={disabled || busy}
          data-testid={`${testIdPrefix}-apply`}
        >
          {busy ? labels.applying : labels.apply}
        </Button>
      </div>
    </div>
  );
}
