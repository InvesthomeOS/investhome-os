/**
 * Right Edit Panel + clean canvas chrome.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-right-edit-panel.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

describe('SMB right edit panel + clean canvas', () => {
  it('removes floating selection toolbar and top format tabs', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.doesNotMatch(workspace, /data-testid="smb-floating-actions"/);
    assert.doesNotMatch(workspace, /smb-ws__format-tabs/);
    assert.doesNotMatch(workspace, /data-testid=\{`smb-format-\$\{f\.key\}`\}/);
    assert.doesNotMatch(workspace, /smb-ws__selection-chrome/);
  });

  it('wires collapsible Düzenle panel with contextual states', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    const panel = readSmb('smb-right-edit-panel.tsx');
    assert.match(workspace, /<SmbRightEditPanel/);
    assert.match(workspace, /editPanelOpen/);
    assert.match(workspace, /smb-ws__layout--edit-collapsed/);
    assert.match(panel, /data-testid="smb-edit-panel"/);
    assert.match(panel, /data-edit-context=\{ctx\}/);
    assert.match(panel, /smb-edit-context-design/);
    assert.match(panel, /smb-structured-slots/);
    assert.match(panel, /smb-edit-context-text/);
    assert.match(panel, /smb-edit-context-image/);
    assert.match(panel, /smb-edit-context-logo/);
    assert.match(panel, /smb-edit-context-cta/);
    assert.match(panel, /smb-edit-context-badge/);
    assert.match(panel, /smb-edit-format-/);
  });

  it('keeps a single 7-action teal bottom bar', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /maxVisible=\{7\}/);
    assert.match(workspace, /singleRow/);
    assert.match(workspace, /dividerAfterKey="variation"/);
    assert.match(workspace, /smb-output-story/);
    assert.match(workspace, /smb-output-reel/);
    assert.match(workspace, /smb-output-variation/);
    assert.match(workspace, /smb-action-undo/);
    assert.match(workspace, /smb-action-redo/);
    assert.match(workspace, /smb-action-download/);
    assert.match(workspace, /smb-action-publish/);
    // No second dock branch with the old component insert toolbar.
    assert.doesNotMatch(workspace, /testIdPrefix="smb-dock-style"/);
    assert.doesNotMatch(workspace, /smb-action-change-image/);
  });

  it('manual panel edits patch layers without GPT Image generate calls', () => {
    const panel = readSmb('smb-right-edit-panel.tsx');
    assert.doesNotMatch(panel, /generateGptImageDesign/);
    assert.doesNotMatch(panel, /runGptImageGenerate/);
    assert.match(panel, /patch\(/);
    assert.match(panel, /onReplaceImage/);
  });
});
