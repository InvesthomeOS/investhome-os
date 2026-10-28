/**
 * CRM correction controls stay behind existing permissions and keep history.
 * Run: node --test src/lib/crm/__tests__/relationship-corrections-ui.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

import { ownershipShareError } from '../ownership-share.ts';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8');
}

const editor = read('src/workspaces/crm/contact-card/agreement-owners-editor.tsx');
const purchase = read('src/workspaces/crm/contact-card/purchase-detail-view.tsx');
const agents = read('src/app/workspaces/crm/agents/_components/agents-list.tsx');
const workspace = read('src/app/workspaces/crm/agents/_components/agents-workspace.tsx');

describe('ownership correction UI', () => {
  it('is shown for ordinary sales edits and confirms that the contact remains', () => {
    assert.match(purchase, /has\('edit_ownership'\)/);
    assert.match(purchase, /has\('update'\)/);
    assert.match(purchase, /data-testid="purchase-unit-edit"/);
    assert.match(purchase, /data-testid="change-unit-confirm"/);
    assert.match(purchase, /changeAgreementUnit/);
    assert.match(purchase, /AgreementOwnersEditor/);
    assert.match(editor, /data-testid="agreement-owners-editor"/);
    assert.match(editor, /data-testid="remove-owner-confirm"/);
    assert.match(editor, /Kişi kaydı ve geçmişi durur/);
    assert.match(editor, /ownershipShareError/);
    assert.match(editor, /replaceAgreementOwners/);
    assert.match(editor, /removeAgreementOwner/);
    assert.equal(ownershipShareError(['100']), null);
    assert.equal(ownershipShareError(['60', '40']), null);
    assert.equal(ownershipShareError(['70', '50']), 'Sahiplik toplamı 100 olmalıdır.');
    assert.doesNotMatch(editor, /deleteContact\(/);
  });
});

describe('agent archive UI', () => {
  it('archives and restores through the agent endpoints after confirmation', () => {
    assert.match(workspace, /has\('archive'\)/);
    assert.match(workspace, /has\('restore'\)/);
    assert.match(workspace, /archiveAgent/);
    assert.match(workspace, /restoreAgent/);
    assert.match(agents, /data-testid="archive-agent-confirm"/);
    assert.match(agents, /geçmiş etkinlikleri silinmez/);
    assert.doesNotMatch(agents, /deleteContact\(/);
  });
});
