/**
 * Portal login next-parameter open-redirect protection.
 * Run: node --test src/lib/auth/__tests__/portal-open-redirect.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import { safePortalPath } from '../portal-session-cookie.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

describe('valid /portal path accepted', () => {
  it('keeps the portal home path', () => {
    assert.equal(safePortalPath('/portal'), '/portal');
  });
});

describe('valid nested portal path accepted', () => {
  it('keeps nested portal destinations', () => {
    assert.equal(safePortalPath('/portal/dashboard'), '/portal/dashboard');
    assert.equal(safePortalPath('/portal/documents/123'), '/portal/documents/123');
  });
});

describe('absolute external URL rejected', () => {
  it('ignores http(s) destinations and falls back to /portal', () => {
    assert.equal(safePortalPath('https://evil.example'), '/portal');
    assert.equal(safePortalPath('http://evil.example'), '/portal');
    assert.equal(safePortalPath('https://evil.example/portal'), '/portal');
  });
});

describe('protocol-relative URL rejected', () => {
  it('ignores //host destinations', () => {
    assert.equal(safePortalPath('//evil.example'), '/portal');
    assert.equal(safePortalPath('//evil.example/portal'), '/portal');
  });
});

describe('javascript/data schemes rejected', () => {
  it('ignores script and data URLs', () => {
    assert.equal(safePortalPath('javascript:alert(1)'), '/portal');
    assert.equal(safePortalPath('data:text/html,hello'), '/portal');
  });
});

describe('encoded/malformed bypass rejected', () => {
  it('rejects encoded slashes, traversal, and leftover encoding tricks', () => {
    assert.equal(safePortalPath('/%2f%2fevil.example'), '/portal');
    assert.equal(safePortalPath('/portal/..//evil.example'), '/portal');
    assert.equal(safePortalPath('/portal/../../login'), '/portal');
    assert.equal(safePortalPath('/portal/%2e%2e/%2e%2e/login'), '/portal');
    assert.equal(safePortalPath('/portal%2f%2fevil.example'), '/portal');
    assert.equal(safePortalPath('/%70ortal/../https://evil.example'), '/portal');
    assert.equal(safePortalPath('\\portal'), '/portal');
  });
});

describe('non-portal internal path rejected', () => {
  it('does not allow staff or other app paths', () => {
    assert.equal(safePortalPath('/dashboard'), '/portal');
    assert.equal(safePortalPath('/login'), '/portal');
    assert.equal(safePortalPath('/workspaces/crm'), '/portal');
    assert.equal(safePortalPath('/portalism'), '/portal');
  });
});

describe('invalid next falls back to /portal', () => {
  it('uses /portal for empty, missing, and junk values', () => {
    assert.equal(safePortalPath(null), '/portal');
    assert.equal(safePortalPath(undefined), '/portal');
    assert.equal(safePortalPath(''), '/portal');
    assert.equal(safePortalPath('   '), '/portal');
    assert.equal(safePortalPath('not-a-path'), '/portal');
  });

  it('portal login uses safePortalPath before replace', () => {
    const login = read('app/portal/login/page.tsx');
    assert.match(login, /safePortalPath\(search\.get\('next'\)\)/);
    assert.doesNotMatch(login, /router\.replace\(next\)/);
    assert.match(login, /router\.replace\(safePortalPath/);
  });
});
