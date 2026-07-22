/**
 * Design asset registry + showcase i18n — D1B.5
 * Run: node src/components/design-system/__tests__/design-asset-registry.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');
const repoRoot = join(webRoot, '../..');

const registryPath = join(repoRoot, 'packages/ui/src/design-asset-registry.ts');
assert.equal(existsSync(registryPath), true, 'design-asset-registry.ts missing');
const registrySrc = readFileSync(registryPath, 'utf8');

assert.match(registrySrc, /DESIGN_ASSET_REGISTRY/);
assert.match(registrySrc, /figmaName:/);
assert.match(registrySrc, /documentationPath:/);

const ids = [...registrySrc.matchAll(/id:\s*'([^']+)'/g)].map((m) => m[1]);
const figmas = [...registrySrc.matchAll(/figmaName:\s*'([^']+)'/g)].map((m) => m[1]);
assert.equal(ids.length, new Set(ids).size, 'unique ids');
assert.equal(figmas.length, new Set(figmas).size, 'unique figma names');

const showcase = readFileSync(
  join(webRoot, 'src/app/dashboard/admin/design-system/_components/design-system-showcase.tsx'),
  'utf8',
);
assert.match(showcase, /DESIGN_ASSET_REGISTRY/);
assert.match(showcase, /getCanonicalDesignAssets/);
assert.match(showcase, /getDeprecatedCandidateAssets/);
assert.match(showcase, /ds-registry-table/);
assert.match(showcase, /sections\.registry/);
// Admin showcase may list Figma names; must not dump filesystem paths in UI labels
assert.doesNotMatch(showcase, /packages\/ui\/src/);
assert.doesNotMatch(showcase, /documentationPath/);

const en = JSON.parse(readFileSync(join(webRoot, 'messages/en.json'), 'utf8'));
const tr = JSON.parse(readFileSync(join(webRoot, 'messages/tr.json'), 'utf8'));
assert.equal(en.designSystem.sections.registry?.length > 0, true);
assert.equal(tr.designSystem.sections.registry?.length > 0, true);
assert.equal(en.designSystem.registryIntro?.length > 0, true);
assert.equal(tr.designSystem.registryIntro?.length > 0, true);
assert.match(en.designSystem.registryCount, /\{total\}/);
assert.match(tr.designSystem.registryCount, /\{total\}/);
assert.equal(en.designSystem.registryStatus.canonical?.length > 0, true);
assert.equal(tr.designSystem.registryStatus.canonical?.length > 0, true);
assert.equal(en.designSystem.registryStatus['deprecated-candidate']?.length > 0, true);
assert.equal(tr.designSystem.registryStatus['deprecated-candidate']?.length > 0, true);

const dsCss = readFileSync(join(webRoot, 'src/app/design-system.css'), 'utf8');
assert.match(dsCss, /ds-chart-container--height-compact/);
assert.match(dsCss, /ds-chart-container--height-hero/);
assert.match(dsCss, /ih-table--density-compact/);
assert.match(dsCss, /ih-table--density-comfortable/);
assert.match(dsCss, /ds-registry-table/);

const docs = [
  'frontend-ui-dependency-audit.md',
  'component-source-of-truth.md',
  'figma-component-map.md',
  'component-variant-contract.md',
  'figma-variables-spec.md',
  'icon-system.md',
  'chart-design-contract.md',
  'table-density-contract.md',
  'responsive-component-contract.md',
  'duplicate-component-matrix.md',
  'ui-migration-plan.md',
  'figma-handoff-template.md',
];
for (const doc of docs) {
  assert.equal(
    existsSync(join(repoRoot, 'docs/design-system', doc)),
    true,
    `missing doc ${doc}`,
  );
}

console.log('design-asset-registry web checks passed');
