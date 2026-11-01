'use client';

import { useTranslations } from 'next-intl';

import type { DocumentPreferences } from '../../_state/documents-state';
import type { LibraryViewMode } from '../../_data/document-types';

export interface DocumentPreferencesDrawerProps {
  open: boolean;
  preferences: DocumentPreferences;
  onClose: () => void;
  onChange: (patch: Partial<DocumentPreferences>) => void;
}

export function DocumentPreferencesDrawer({
  open,
  preferences,
  onClose,
  onChange,
}: DocumentPreferencesDrawerProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tCommon = useTranslations('common');
  if (!open) return null;

  return (
    <div className="inv-docs__drawer-overlay" role="dialog" aria-modal="true" aria-labelledby="doc-prefs-title">
      <div className="inv-docs__drawer">
        <header className="inv-docs__drawer-header">
          <h2 id="doc-prefs-title">{tChrome('k13d64d1f05')}</h2>
          <button type="button" onClick={onClose} aria-label={tChrome('ke9bbd004de')}>
            ✕
          </button>
        </header>
        <div className="inv-docs__drawer-body">
          <p className="inv-docs__prefs-note">
            These settings are stored locally for demo continuity. No changes are sent to a server.
          </p>

          <label className="inv-docs__pref-toggle">
            <input
              type="checkbox"
              checked={preferences.emailNotifications}
              onChange={(e) => onChange({ emailNotifications: e.target.checked })}
            />
            Email notifications for new documents
          </label>

          <label className="inv-docs__pref-toggle">
            <input
              type="checkbox"
              checked={preferences.autoArchiveSigned}
              onChange={(e) => onChange({ autoArchiveSigned: e.target.checked })}
            />
            Auto-archive documents after signing (demo)
          </label>

          <label className="inv-docs__pref-field">
            <span>{tChrome('k0d527fb1bf')}</span>
            <select
              value={preferences.defaultView}
              onChange={(e) =>
                onChange({ defaultView: e.target.value as LibraryViewMode })
              }
            >
              <option value="table">{tChrome('k0424f6e702')}</option>
              <option value="grid">{tChrome('k701c483f81')}</option>
              <option value="folder">{tChrome('k30baa24967')}</option>
            </select>
          </label>

          <label className="inv-docs__pref-field">
            <span>{tChrome('k5a982761fc')}</span>
            <select
              value={preferences.downloadFormat}
              onChange={(e) =>
                onChange({
                  downloadFormat: e.target.value as DocumentPreferences['downloadFormat'],
                })
              }
            >
              <option value="original">{tChrome('k32d4ceda71')}</option>
              <option value="pdf">{tChrome('kceeb2eb55c')}</option>
            </select>
          </label>
        </div>
        <footer className="inv-docs__drawer-footer">
          <button type="button" className="inv-docs__btn inv-docs__btn--primary" onClick={onClose}>
            Done
          </button>
        </footer>
      </div>
      <button type="button" className="inv-docs__drawer-backdrop" onClick={onClose} aria-label={tCommon('close')} tabIndex={-1} />
    </div>
  );
}
