/**
 * packages/ui Design System export / token checks.
 * Run: node src/design-system.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const index = readFileSync(join(root, 'components/index.ts'), 'utf8');

for (const name of [
  'WidgetShell',
  'MetricCard',
  'Surface',
  'StatusBadge',
  'TrendIndicator',
  'SkeletonState',
  'ChartContainer',
  'IconButton',
  'FilterButton',
  'SegmentedControl',
  'DateRangeControl',
  'WidgetMenu',
  'RightRailCard',
  'CardHeader',
  'CardContent',
  'CardFooter',
]) {
  assert.match(index, new RegExp(`export \\{[^}]*\\b${name}\\b`));
}

assert.equal(existsSync(join(root, 'design-tokens.ts')), true);
const designTokens = readFileSync(join(root, 'design-tokens.ts'), 'utf8');
assert.match(designTokens, /spacing/);
assert.match(designTokens, /\b6:\s*6/);
assert.match(designTokens, /statusAi/);
assert.match(designTokens, /#9D7B55|#9d7b55|brandTokens\.primary/);
assert.match(designTokens, /medium:/);

assert.equal(existsSync(join(root, 'design-asset-registry.ts')), true);
const registry = readFileSync(join(root, 'design-asset-registry.ts'), 'utf8');
assert.match(registry, /DESIGN_ASSET_REGISTRY/);
assert.match(registry, /MetricCard/);

const card = readFileSync(join(root, 'components/Card.tsx'), 'utf8');
assert.match(card, /title\?:/);

const empty = readFileSync(join(root, 'components/EmptyState.tsx'), 'utf8');
assert.match(empty, /compact\?:/);

console.log('packages/ui design-system checks passed');
