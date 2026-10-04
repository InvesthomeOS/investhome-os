/**
 * Portal cookie surface has no privileged cookie-authenticated mutations.
 * Run: node --test src/lib/auth/__tests__/portal-csrf-surface.test.mjs
 */

import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

function collectSourceFiles(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      if (entry === '__tests__' || entry === 'node_modules') continue;
      collectSourceFiles(full, files);
      continue;
    }
    if (/\.(ts|tsx|mjs|js)$/.test(entry)) files.push(full);
  }
  return files;
}

function exportedHandlers(source) {
  const found = new Set();
  for (const method of ['GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE']) {
    if (new RegExp(`export async function ${method}\\b`).test(source)) {
      found.add(method);
    }
  }
  return found;
}

describe('portal API mutation surface', () => {
  const portalApiRoot = join(webSrc, 'app/api/portal');
  const routeFiles = collectSourceFiles(portalApiRoot).filter((file) => file.endsWith('route.ts'));

  it('only exposes session POST/DELETE and GET download — no PUT/PATCH', () => {
    const byRel = Object.fromEntries(
      routeFiles.map((file) => [relative(portalApiRoot, file).replaceAll('\\', '/'), readFileSync(file, 'utf8')]),
    );
    assert.deepEqual(Object.keys(byRel).sort(), [
      'documents/[documentId]/download/route.ts',
      'session/route.ts',
    ]);

    const session = exportedHandlers(byRel['session/route.ts']);
    assert.deepEqual([...session].sort(), ['DELETE', 'GET', 'POST']);
    const download = exportedHandlers(byRel['documents/[documentId]/download/route.ts']);
    assert.deepEqual([...download].sort(), ['GET']);

    for (const source of Object.values(byRel)) {
      assert.equal(exportedHandlers(source).has('PUT'), false);
      assert.equal(exportedHandlers(source).has('PATCH'), false);
    }
  });

  it('does not authenticate POST login from the portal cookie', () => {
    const session = read('app/api/portal/session/route.ts');
    const post = session.slice(session.indexOf('export async function POST'));
    const postBody = post.slice(0, post.indexOf('export async function DELETE'));
    assert.match(postBody, /authenticatePortalDemo/);
    assert.match(postBody, /body\?\.email/);
    assert.match(postBody, /body\?\.password/);
    assert.doesNotMatch(postBody, /decodePortalSession/);
    assert.doesNotMatch(postBody, /jar\.get\(PORTAL_SESSION_COOKIE\)/);
  });

  it('treats DELETE logout as cookie-clear, not a session-gated mutation', () => {
    const session = read('app/api/portal/session/route.ts');
    const del = session.slice(session.indexOf('export async function DELETE'));
    assert.match(del, /jar\.set\(PORTAL_SESSION_COOKIE, ''/);
    assert.match(del, /maxAge:\s*0/);
    assert.doesNotMatch(del, /decodePortalSession/);
    assert.doesNotMatch(del, /authenticatePortalDemo/);
  });

  it('gates the only cookie-authenticated portal route with GET', () => {
    const download = read('app/api/portal/documents/[documentId]/download/route.ts');
    assert.match(download, /export async function GET/);
    assert.match(download, /decodePortalSession/);
    assert.match(download, /canDownloadDocument/);
    assert.doesNotMatch(download, /export async function (POST|PUT|PATCH|DELETE)/);
    const sessionGet = read('app/api/portal/session/route.ts');
    const get = sessionGet.slice(
      sessionGet.indexOf('export async function GET'),
      sessionGet.indexOf('export async function POST'),
    );
    assert.match(get, /decodePortalSession/);
  });
});

describe('portal client does not mint cookie-authenticated mutations', () => {
  it('only POSTs login credentials and DELETE-clears the session cookie', () => {
    const login = read('app/portal/login/page.tsx');
    assert.match(login, /method:\s*'POST'/);
    assert.match(login, /JSON\.stringify\(\{ email, password \}\)/);
    assert.doesNotMatch(login, /method:\s*'(PUT|PATCH|DELETE)'/);

    const portalState = read('app/portal/_state/portal-session.tsx');
    assert.match(portalState, /method:\s*'DELETE'/);
    assert.match(portalState, /credentials:\s*'include'/);
    assert.doesNotMatch(portalState, /method:\s*'(POST|PUT|PATCH)'/);

    const documents = read('app/portal/_components/modules/documents-view.tsx');
    assert.match(documents, /\/api\/portal\/documents\/\$\{docId\}\/download/);
    assert.doesNotMatch(documents, /method:\s*'(POST|PUT|PATCH|DELETE)'/);
  });

  it('does not add a portal CSRF middleware that staff Bearer clients would hit', () => {
    const middleware = read('middleware.ts');
    assert.doesNotMatch(middleware, /X-CSRF-Token|csrf_rejected|portal csrf/i);
    const sessionRoute = read('app/api/portal/session/route.ts');
    assert.doesNotMatch(sessionRoute, /csrf/i);
    const download = read('app/api/portal/documents/[documentId]/download/route.ts');
    assert.doesNotMatch(download, /csrf/i);
  });
});
