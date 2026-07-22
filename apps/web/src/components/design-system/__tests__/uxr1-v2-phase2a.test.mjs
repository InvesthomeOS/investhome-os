/**
 * UXR1 V2 Phase 2A — Production shell + Dashboard migration contract checks.
 * Run: node src/components/design-system/__tests__/uxr1-v2-phase2a.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');
const repoRoot = join(webRoot, '../..');

function read(relFromWeb) {
  return readFileSync(join(webRoot, relFromWeb), 'utf8');
}

function readRepo(rel) {
  return readFileSync(join(repoRoot, rel), 'utf8');
}

// --- Route helper ---
const dsVersionSrc = read('src/lib/theme/ds-version.ts');
assert.match(dsVersionSrc, /isDsV2ShellRoute/);
assert.match(dsVersionSrc, /\/dashboard\/executive/);
assert.match(dsVersionSrc, /DS_VERSION_V2/);

// Inline mirror of route rules for unit assertions
function isDsV2ShellRoute(pathname) {
  if (!pathname) return false;
  const path = pathname.split('?')[0]?.split('#')[0] ?? pathname;
  if (path === '/dashboard' || path === '/dashboard/') return true;
  if (path === '/dashboard/executive' || path.startsWith('/dashboard/executive/')) return true;
  return false;
}

assert.equal(isDsV2ShellRoute('/dashboard'), true);
assert.equal(isDsV2ShellRoute('/dashboard/'), true);
assert.equal(isDsV2ShellRoute('/dashboard/executive'), true);
assert.equal(isDsV2ShellRoute('/dashboard/executive?view=legacy'), true);
assert.equal(isDsV2ShellRoute('/dashboard/sales'), false);
assert.equal(isDsV2ShellRoute('/dashboard/crm'), false);
assert.equal(isDsV2ShellRoute('/dashboard/leads'), false);
assert.equal(isDsV2ShellRoute('/dashboard/marketing'), false);
assert.equal(isDsV2ShellRoute('/dashboard/investors'), false);
assert.equal(isDsV2ShellRoute('/dashboard/projects'), false);
assert.equal(isDsV2ShellRoute(null), false);

// --- OsShell scoped activation ---
const osShell = read('src/components/shell/os-shell.tsx');
assert.match(osShell, /isDsV2ShellRoute/);
assert.match(osShell, /data-ds-version/);
assert.match(osShell, /os-shell-v2/);
assert.match(osShell, /usePathname/);

// --- Shell V2 CSS scoped (no global leakage patterns) ---
assert.equal(existsSync(join(webRoot, 'src/app/shell-v2.css')), true, 'shell-v2.css missing');
const shellV2 = read('src/app/shell-v2.css');
assert.match(shellV2, /\[data-ds-version='v2'\]/);
assert.match(shellV2, /\.dashboard-shell\[data-ds-version='v2'\]/);
assert.match(shellV2, /--ih-ui-canvas-muted/);
assert.match(shellV2, /--ih-blue-50/);
assert.match(shellV2, /\.ex-home__hero/);
assert.match(shellV2, /\.ds-exec-g8/);
// No unscoped shell canvas rewrite (must require data-ds-version)
assert.doesNotMatch(shellV2, /^\.dashboard-shell\s*\{/m);
assert.match(shellV2, /\.dashboard-shell\[data-ds-version='v2'\],\s*\n\[data-ds-version='v2'\]\.dashboard-shell/);

const layout = read('src/app/layout.tsx');
assert.match(layout, /shell-v2\.css/);

// --- Tokens ---
const tokens = read('src/app/theme-tokens.css');
assert.match(tokens, /\[data-ds-version='v2'\]/);
assert.match(tokens, /--ih-shell-content-pad-x/);
assert.match(tokens, /--ih-section-gap/);
assert.match(tokens, /--radius-large:\s*var\(--radius-card\)/);

const designTokens = readRepo('packages/ui/src/design-tokens.ts');
assert.match(designTokens, /uxr1V2Tokens/);
assert.match(designTokens, /shellContentPadX/);
assert.match(designTokens, /sectionGap/);

// --- UI primitives ---
const uiPrim = readRepo('packages/ui/src/components/DashboardPrimitives.tsx');
assert.match(uiPrim, /export function V2Card/);
assert.match(uiPrim, /export function DashboardPanel/);
assert.match(uiPrim, /export function ActionButtonGroup/);
assert.match(uiPrim, /export function ProgressIndicator/);
assert.match(uiPrim, /role="progressbar"/);
assert.match(uiPrim, /aria-valuenow/);

const uiIndex = readRepo('packages/ui/src/components/index.ts');
assert.match(uiIndex, /V2Card/);
assert.match(uiIndex, /DashboardPanel/);
assert.match(uiIndex, /ActionButtonGroup/);
assert.match(uiIndex, /ProgressIndicator/);

// --- Dashboard surfaces marked ---
const home = read('src/app/dashboard/_components/executive-home.tsx');
assert.match(home, /dashboard-home-v2/);
assert.match(home, /ProgressIndicator/);
assert.doesNotMatch(home, /ProgressBar/);

const g8 = read(
  'src/app/dashboard/executive/_components/production-dashboard/g8/g8-executive-dashboard.tsx',
);
assert.match(g8, /data-ds-surface="v2"/);
assert.match(g8, /executive-dashboard-g8/);
assert.match(g8, /MetricCard/);
assert.match(g8, /WidgetShell/);

// Metric card V2 card tokens in design-system.css
const dsCss = read('src/app/design-system.css');
assert.match(dsCss, /\.ds-metric-card/);
assert.match(dsCss, /--radius-card/);
assert.match(dsCss, /--shadow-card-premium/);

// Docs SoT still present
assert.equal(existsSync(join(repoRoot, 'docs/design-system/investhome-os-design-system-v2.md')), true);
assert.equal(existsSync(join(repoRoot, 'artifacts/uxr1-v2/REPORT.md')), true);

console.log('uxr1-v2-phase2a.test.mjs: ok');
