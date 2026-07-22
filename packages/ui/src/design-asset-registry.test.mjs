/**
 * Design asset registry validity — D1B.5
 * Run: node src/design-asset-registry.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
// src → packages/ui → packages → repo root
const repoRoot = join(root, '../../..');
const src = readFileSync(join(root, 'design-asset-registry.ts'), 'utf8');

assert.match(src, /export const DESIGN_ASSET_REGISTRY/);
assert.match(src, /export interface DesignAssetEntry/);
assert.match(src, /getCanonicalDesignAssets/);
assert.match(src, /getDeprecatedCandidateAssets/);

const index = readFileSync(join(root, 'index.ts'), 'utf8');
assert.match(index, /DESIGN_ASSET_REGISTRY/);
assert.match(index, /design-asset-registry/);

/** Lightweight parse of registry object literals for uniqueness checks */
const idMatches = [...src.matchAll(/id:\s*'([^']+)'/g)].map((m) => m[1]);
const figmaMatches = [...src.matchAll(/figmaName:\s*'([^']+)'/g)].map((m) => m[1]);

assert.ok(idMatches.length >= 20, `expected >=20 registry ids, got ${idMatches.length}`);
assert.equal(idMatches.length, new Set(idMatches).size, 'registry ids must be unique');
assert.equal(figmaMatches.length, new Set(figmaMatches).size, 'figma names must be unique');

for (const id of idMatches) {
  assert.match(id, /^[a-z0-9-]+$/, `invalid id: ${id}`);
}

const requiredFields = [
  'id:',
  'category:',
  'codeName:',
  'importPath:',
  'figmaName:',
  'variants:',
  'states:',
  'sizes:',
  'status:',
  'owner:',
  'documentationPath:',
];
for (const field of requiredFields) {
  assert.ok(src.includes(field), `missing field pattern ${field}`);
}

const docPaths = [...src.matchAll(/documentationPath:\s*'([^']+)'/g)].map((m) => m[1]);
for (const docPath of docPaths) {
  assert.ok(
    existsSync(join(repoRoot, docPath)),
    `documentationPath missing on disk: ${docPath}`,
  );
}

const importPaths = [...src.matchAll(/importPath:\s*'([^']+)'/g)].map((m) => m[1]);
for (const importPath of importPaths) {
  assert.ok(
    importPath.startsWith('@investhome/ui') ||
      importPath.startsWith('@/components/') ||
      importPath.startsWith('apps/'),
    `unexpected importPath: ${importPath}`,
  );
}

assert.match(src, /status: 'canonical'/);
assert.match(src, /status: 'deprecated-candidate'/);
assert.match(src, /Primitive \/ Button/);
assert.match(src, /Data Display \/ Metric Card/);
assert.match(src, /Data Display \/ Widget Shell/);

console.log('design-asset-registry checks passed');
