/**
 * Settings navigation has one home per entry and hides admin links from Sales.
 * Run: node --test src/lib/settings/__tests__/settings-catalog.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

import {
  duplicateSettingHrefs,
  isSettingsTabAllowed,
  SETTINGS_CATALOG,
  visibleSettingsEntries,
} from '../settings-catalog.ts';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8');
}

function user(permissions) {
  return { permissions };
}

const sales = user(['crm:read', 'sales:view', 'notifications:view', 'documents:view']);
const admin = user(['*:*']);
const companyOnly = user(['company:view']);

describe('settings catalog', () => {
  it('gives every catalog entry a unique href', () => {
    assert.deepEqual(duplicateSettingHrefs(SETTINGS_CATALOG), []);
    const ids = SETTINGS_CATALOG.map((entry) => entry.id);
    assert.equal(new Set(ids).size, ids.length);
  });

  it('shows a sales user only personal and CRM settings', () => {
    const ids = visibleSettingsEntries(sales).map((entry) => entry.id).sort();
    assert.deepEqual(ids, ['communicationAccounts', 'crmSettings', 'profile']);
    assert.equal(isSettingsTabAllowed(sales, 'integrations'), false);
    assert.equal(isSettingsTabAllowed(sales, 'company'), false);
    assert.equal(visibleSettingsEntries(sales).some((entry) => entry.href.startsWith('/dashboard/admin')), false);
  });

  it('shows an administrator the access, security, platform, and integration homes', () => {
    const ids = new Set(visibleSettingsEntries(admin).map((entry) => entry.id));
    for (const id of ['profile', 'company', 'integrations', 'communicationAccounts', 'crmSettings', 'users', 'roles', 'security', 'sessions', 'audit']) {
      assert.equal(ids.has(id), true, id);
    }
    assert.deepEqual(duplicateSettingHrefs(visibleSettingsEntries(admin)), []);
  });

  it('does not treat users:view as access to the security page', () => {
    const ids = visibleSettingsEntries(user(['users:view', 'users:manage'])).map((entry) => entry.id);
    assert.equal(ids.includes('users'), true);
    assert.equal(ids.includes('security'), false);
    assert.equal(isSettingsTabAllowed(user(['users:view']), 'integrations'), false);
  });

  it('does not open platform tabs for a company-only user', () => {
    const tabs = visibleSettingsEntries(companyOnly).filter((entry) => entry.tab).map((entry) => entry.tab);
    assert.deepEqual(tabs, ['company']);
    assert.equal(isSettingsTabAllowed(companyOnly, 'ai'), false);
    assert.equal(isSettingsTabAllowed(companyOnly, 'integrations'), false);
  });
});

describe('settings surfaces', () => {
  it('keeps CRM settings on CRM behavior and links elsewhere', () => {
    const crm = read('src/app/workspaces/crm/settings/_components/crm-settings-live-workspace.tsx');
    assert.match(crm, /communication-accounts/);
    assert.match(crm, /data-testid="crm-settings-workspace"/);
    assert.doesNotMatch(crm, /fetchUsers|fetchRoles|fetchMfaPolicy|fetchApiKeys|fetchSystemHealth/);
    assert.match(read('src/app/workspaces/crm/settings/page.tsx'), /CrmSettingsLiveWorkspace/);
  });

  it('keeps Gmail and Meta on the communication accounts page', () => {
    const accounts = read('src/app/workspaces/crm/settings/_components/communication-accounts-view.tsx');
    assert.match(accounts, /startGmailAuthorize/);
    assert.match(accounts, /meta/);
    assert.match(accounts, /whatsapp/);
  });

  it('gates dashboard settings tabs and admin navigation from the catalog', () => {
    const settings = read('src/app/dashboard/settings/_components/settings-workspace.tsx');
    const adminNav = read('src/app/dashboard/admin/_components/admin-shell.tsx');
    const adminHome = read('src/app/dashboard/admin/page.tsx');
    assert.match(settings, /visibleSettingsEntries/);
    assert.match(settings, /isSettingsTabAllowed/);
    assert.match(adminNav, /visibleSettingsEntries/);
    assert.doesNotMatch(adminNav, /tab=company|tab=offices|tab=notifications/);
    assert.doesNotMatch(adminHome, /tab=company|tab=offices|tab=organization|tab=notifications/);
    assert.match(adminHome, /\/dashboard\/settings/);
  });

  it('still sends unauthorized admin routes to the existing guards', () => {
    const users = read('src/app/dashboard/admin/users/_components/users-admin-workspace.tsx');
    const security = read('src/app/dashboard/admin/security/_components/security-dashboard-workspace.tsx');
    const rail = read('src/app/workspaces/crm/_components/crm-sidebar.tsx');
    assert.match(users, /canViewUsers/);
    assert.match(users, /\/forbidden/);
    assert.match(security, /hasPermission\(user, 'security', 'view'\)/);
    assert.match(security, /\/forbidden/);
    assert.doesNotMatch(security, /users', 'view'/);
    assert.doesNotMatch(rail, /platform\/integrations/);
  });
});
