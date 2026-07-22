'use client';

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
  if (!open) return null;

  return (
    <div className="inv-docs__drawer-overlay" role="dialog" aria-modal="true" aria-labelledby="doc-prefs-title">
      <div className="inv-docs__drawer">
        <header className="inv-docs__drawer-header">
          <h2 id="doc-prefs-title">Document Preferences</h2>
          <button type="button" onClick={onClose} aria-label="Close preferences">
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
            <span>Default library view</span>
            <select
              value={preferences.defaultView}
              onChange={(e) =>
                onChange({ defaultView: e.target.value as LibraryViewMode })
              }
            >
              <option value="table">Table</option>
              <option value="grid">Grid</option>
              <option value="folder">Folder</option>
            </select>
          </label>

          <label className="inv-docs__pref-field">
            <span>Download format preference</span>
            <select
              value={preferences.downloadFormat}
              onChange={(e) =>
                onChange({
                  downloadFormat: e.target.value as DocumentPreferences['downloadFormat'],
                })
              }
            >
              <option value="original">Original format</option>
              <option value="pdf">PDF (demo placeholder)</option>
            </select>
          </label>
        </div>
        <footer className="inv-docs__drawer-footer">
          <button type="button" className="inv-docs__btn inv-docs__btn--primary" onClick={onClose}>
            Done
          </button>
        </footer>
      </div>
      <button type="button" className="inv-docs__drawer-backdrop" onClick={onClose} aria-label="Close" tabIndex={-1} />
    </div>
  );
}
