/**
 * Creative Studio builder bootstrap / hydration lifecycle.
 * Run: node --test src/app/workspaces/creative-studio/_components/__tests__/cs-builder-bootstrap.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const componentsDir = join(here, '..');
const studioDir = join(here, '../..');

function read(rel) {
  return readFileSync(join(componentsDir, rel), 'utf8');
}

function readStudio(rel) {
  return readFileSync(join(studioDir, rel), 'utf8');
}

/** Mirrors cs-builder-bootstrap.ts for timeout behavior coverage. */
async function withCsBuilderTimeout(promise, options = {}) {
  const timeoutMs = options.timeoutMs ?? 45_000;
  const message =
    options.message ?? `Builder bootstrap timed out after ${Math.round(timeoutMs / 1000)}s`;
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(message)), timeoutMs);
      }),
    ]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

describe('cs-builder-bootstrap helpers', () => {
  it('ships timeout helper module', () => {
    const src = read('cs-builder-bootstrap.ts');
    assert.match(src, /CS_BUILDER_BOOTSTRAP_TIMEOUT_MS = 45_000/);
    assert.match(src, /export async function withCsBuilderTimeout/);
  });

  it('timeout rejects when the promise hangs', async () => {
    await assert.rejects(
      () =>
        withCsBuilderTimeout(
          new Promise(() => {
            /* never resolves */
          }),
          { timeoutMs: 40, message: 'timed out' },
        ),
      /timed out/,
    );
  });

  it('timeout resolves successful bootstrap results including null draft', async () => {
    const value = await withCsBuilderTimeout(Promise.resolve(null), { timeoutMs: 200 });
    assert.equal(value, null);
  });
});

describe('shared hydration + bootstrap UI wiring', () => {
  it('ships shared hydration hook and bootstrap view', () => {
    assert.ok(existsSync(join(componentsDir, 'use-cs-builder-hydration.ts')));
    assert.ok(existsSync(join(componentsDir, 'cs-builder-bootstrap-view.tsx')));
    assert.ok(existsSync(join(componentsDir, 'cs-builder-bootstrap-view.css')));
  });

  it('hydration hook uses generation invalidation for Strict Mode', () => {
    const src = read('use-cs-builder-hydration.ts');
    assert.match(src, /genRef/);
    assert.match(src, /setPhase\('ready'\)/);
    assert.match(src, /setPhase\('error'\)/);
    assert.match(src, /onSuccessRef\.current\(result\.draft\)/);
    assert.match(src, /genRef\.current \+= 1/);
  });

  it('bootstrap view keeps header chrome and DS loading/error states', () => {
    const src = read('cs-builder-bootstrap-view.tsx');
    assert.match(src, /LoadingState/);
    assert.match(src, /ErrorState/);
    assert.match(src, /cs-builder-bootstrap__header/);
    assert.match(src, /onRetry/);
    assert.doesNotMatch(src, /wb-ws--skeleton/);
  });

  it('document hooks guard bootstrap with generation + timeout', () => {
    const builder = read('use-builder-document.ts');
    const website = readStudio('website-builder/use-website-builder-document.ts');
    for (const src of [builder, website]) {
      assert.match(src, /bootGenRef/);
      assert.match(src, /withCsBuilderTimeout/);
      assert.match(src, /gen !== bootGenRef\.current/);
      assert.match(src, /Empty\/new docs resolve as draft=null/);
    }
  });

  it('all seven production builders use shared hydration gate', () => {
    const builders = [
      ['website-builder/website-builder-workspace.tsx', 'wb-workspace-loading'],
      ['landing-page-builder/landing-page-builder-workspace.tsx', 'lpb-workspace-loading'],
      ['blog-builder/blog-builder-workspace.tsx', 'bb-workspace-loading'],
      ['email-builder/email-builder-workspace.tsx', 'eb-workspace-loading'],
      ['proposal-builder/proposal-builder-workspace.tsx', 'prb-workspace-loading'],
      ['presentation-builder/presentation-builder-workspace.tsx', 'pb-workspace-loading'],
      ['social-media-builder/social-media-builder-workspace.tsx', 'smb-workspace-loading'],
    ];
    for (const [rel, testId] of builders) {
      const src = readStudio(rel);
      assert.match(src, /useCsBuilderHydration/, rel);
      assert.match(src, /CsBuilderBootstrapView/, rel);
      assert.match(src, new RegExp(testId), rel);
      assert.match(src, /hydration\.phase !== 'ready'/, rel);
      assert.doesNotMatch(src, /setHydrated\(false\)/, rel);
    }
  });

  it('preserves SMB delete-race wait loop from 8454502', () => {
    const src = read('use-builder-document.ts');
    assert.match(src, /Wait out in-flight saves instead of dropping/);
    assert.match(src, /while \(savingRef\.current\)/);
  });

  it('CS breadcrumb targets /workspaces/creative-studio without /dashboard', () => {
    const crumbs = readFileSync(
      join(studioDir, '../../dashboard/_components/breadcrumbs.tsx'),
      'utf8',
    );
    assert.match(crumbs, /workspaceId === 'creative-studio'/);
    assert.match(crumbs, /\/workspaces\/creative-studio'/);
  });
});
