/**
 * Focused Design System v1.0 foundation checks.
 * Run: node src/components/design-system/__tests__/design-system.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
// __tests__ → design-system → components → src → apps/web
const webRoot = join(here, '../../../..');
const repoRoot = join(webRoot, '../..');

function read(relFromWeb) {
  return readFileSync(join(webRoot, relFromWeb), 'utf8');
}

// Route
assert.equal(
  existsSync(join(webRoot, 'src/app/dashboard/admin/design-system/page.tsx')),
  true,
  'design-system showcase route missing',
);

// Tokens
const tokens = read('src/app/theme-tokens.css');
for (const name of [
  '--background-canvas',
  '--surface-default',
  '--border-default',
  '--text-primary',
  '--brand-primary-ds',
  '--status-success',
  '--status-ai',
  '--space-24px',
  '--radius-large',
  '--shadow-card',
  '--font-size-metric-large',
]) {
  assert.match(tokens, new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
}

// Layout primitives
for (const file of [
  'layout/AppPage.tsx',
  'layout/PageHeader.tsx',
  'layout/PageSection.tsx',
  'layout/DashboardGrid.tsx',
  'layout/DashboardRow.tsx',
  'layout/WidgetColumn.tsx',
  'layout/RightRail.tsx',
  'layout/ContentContainer.tsx',
]) {
  assert.equal(existsSync(join(webRoot, 'src/components/design-system', file)), true, file);
}

// Chart wrappers
for (const file of [
  'charts/LineChart.tsx',
  'charts/AreaChart.tsx',
  'charts/BarChart.tsx',
  'charts/DonutChart.tsx',
  'charts/FunnelChart.tsx',
  'charts/ProgressChart.tsx',
  'charts/Sparkline.tsx',
  'charts/TimelineChart.tsx',
  'charts/HeatmapChart.tsx',
  'charts/format.ts',
]) {
  assert.equal(existsSync(join(webRoot, 'src/components/design-system', file)), true, file);
}

// packages/ui primitives
const uiRoot = join(repoRoot, 'packages/ui/src/components');
for (const file of [
  'WidgetShell.tsx',
  'MetricCard.tsx',
  'Surface.tsx',
  'StatusBadge.tsx',
  'TrendIndicator.tsx',
  'SkeletonState.tsx',
  'ChartContainer.tsx',
  'IconButton.tsx',
  'FilterButton.tsx',
  'SegmentedControl.tsx',
  'DateRangeControl.tsx',
  'WidgetMenu.tsx',
  'RightRailCard.tsx',
  'CardHeader.tsx',
  'CardContent.tsx',
  'CardFooter.tsx',
]) {
  assert.equal(existsSync(join(uiRoot, file)), true, `ui:${file}`);
}

// WidgetShell contract
const widgetShell = readFileSync(join(uiRoot, 'WidgetShell.tsx'), 'utf8');
assert.match(widgetShell, /state\?: WidgetShellState/);
assert.match(widgetShell, /span\?: WidgetSpan/);
assert.match(widgetShell, /EmptyState/);
assert.match(widgetShell, /ErrorState/);
assert.match(widgetShell, /SkeletonState/);
assert.match(widgetShell, /aria-label/);

// MetricCard states
const metricCard = readFileSync(join(uiRoot, 'MetricCard.tsx'), 'utf8');
assert.match(metricCard, /loading\?:/);
assert.match(metricCard, /empty\?:/);
assert.match(metricCard, /error\?:/);

// Grid CSS
const dsCss = read('src/app/design-system.css');
assert.match(dsCss, /\.ds-dashboard-grid/);
assert.match(dsCss, /--ds-grid-cols-desktop/);
assert.match(dsCss, /grid-template-columns: 1fr/);
assert.match(dsCss, /\.ds-widget-shell/);
assert.match(dsCss, /box-shadow: var\(--shadow-card\)/);

// Chart format helpers
const formatSrc = read('src/components/design-system/charts/format.ts');
assert.match(formatSrc, /currency/);
assert.match(formatSrc, /percent/);
assert.match(formatSrc, /compact/);
assert.match(formatSrc, /DS_CHART_COLORS/);

// i18n keys
const en = JSON.parse(readFileSync(join(webRoot, 'messages/en.json'), 'utf8'));
const tr = JSON.parse(readFileSync(join(webRoot, 'messages/tr.json'), 'utf8'));
assert.equal(en.adminShell.nav.designSystem?.length > 0, true);
assert.equal(tr.adminShell.nav.designSystem?.length > 0, true);
assert.equal(en.designSystem.title.includes('Design System'), true);
assert.equal(tr.designSystem.title.includes('Tasarım'), true);
assert.equal(en.designSystem.sections.widgets?.length > 0, true);
assert.equal(tr.designSystem.sections.charts?.length > 0, true);
assert.equal(en.designSystem.eyebrow, 'INVESTHOME OS');
assert.equal(tr.designSystem.eyebrow, 'INVESTHOME OS');

// Docs
assert.equal(existsSync(join(repoRoot, 'docs/design-system/current-ui-audit.md')), true);
assert.equal(existsSync(join(repoRoot, 'docs/design-system/navigation-map.md')), true);
assert.equal(existsSync(join(repoRoot, 'docs/design-system/investhome-os-design-system-v1.md')), true);
assert.equal(
  existsSync(join(repoRoot, 'docs/design-system/executive-dashboard-information-architecture.md')),
  true,
);
assert.equal(
  existsSync(join(repoRoot, 'docs/design-system/figma-component-map.md')),
  true,
);
assert.equal(
  existsSync(join(repoRoot, 'packages/ui/src/design-asset-registry.ts')),
  true,
);
assert.equal(en.designSystem.sections.registry?.length > 0, true);
assert.equal(tr.designSystem.sections.registry?.length > 0, true);

// Product naming guard in docs
const spec = readFileSync(join(repoRoot, 'docs/design-system/investhome-os-design-system-v1.md'), 'utf8');
assert.match(spec, /INVESTHOME OS/);
assert.match(spec, /Dashboard Information Hierarchy/);
assert.match(spec, /\/dashboard\/admin\/design-system/);

console.log('design-system foundation checks passed');
