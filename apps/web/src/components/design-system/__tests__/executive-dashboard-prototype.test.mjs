/**
 * Focused Design Sprint D1C executive dashboard visual prototype checks.
 * Run: node src/components/design-system/__tests__/executive-dashboard-prototype.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');
const repoRoot = join(webRoot, '../..');

function read(relFromWeb) {
  return readFileSync(join(webRoot, relFromWeb), 'utf8');
}

const routePage = 'src/app/dashboard/admin/design-system/executive-dashboard/page.tsx';
const protoFile =
  'src/app/dashboard/admin/design-system/executive-dashboard/_components/executive-dashboard-prototype.tsx';
const demoData =
  'src/app/dashboard/admin/design-system/executive-dashboard/_components/prototype-demo-data.ts';

assert.equal(existsSync(join(webRoot, routePage)), true, 'prototype route page missing');
assert.equal(existsSync(join(webRoot, protoFile)), true, 'prototype component missing');
assert.equal(existsSync(join(webRoot, demoData)), true, 'prototype demo data missing');

const pageSrc = read(routePage);
assert.match(pageSrc, /ExecutiveDashboardPrototype/);
assert.match(pageSrc, /prototype ONLY/i);
assert.match(pageSrc, /not the production executive/i);
assert.match(pageSrc, /canViewUsers/);
assert.match(pageSrc, /canViewRoles/);
assert.match(pageSrc, /\/forbidden/);
assert.match(pageSrc, /Admin-only|admin-only/i);

const protoSrc = read(protoFile);
assert.match(protoSrc, /data-testid="executive-dashboard-prototype"/);
assert.match(protoSrc, /PROTOTYPE_DEMO_BANNER/);
assert.match(protoSrc, /data-sprint="D1C"/);
assert.match(protoSrc, /exec-proto-section-alerts/);
assert.match(protoSrc, /exec-proto-section-kpis/);
assert.match(protoSrc, /exec-proto-section-decision-finance/);
assert.match(protoSrc, /exec-proto-section-work/);
assert.match(protoSrc, /exec-proto-section-pipeline-projects/);
assert.match(protoSrc, /exec-proto-section-projects-marketing/);
assert.match(protoSrc, /exec-proto-section-comms/);
assert.match(protoSrc, /exec-proto-tasks-widget/);
assert.match(protoSrc, /exec-proto-calendar-widget/);
assert.match(protoSrc, /exec-proto-ai-widget/);
assert.match(protoSrc, /exec-proto-comms-widget/);
assert.match(protoSrc, /exec-proto-sales-widget/);
assert.match(protoSrc, /exec-proto-investors-widget/);
assert.match(protoSrc, /exec-proto-projects-widget/);
assert.match(protoSrc, /exec-proto-marketing-widget/);
assert.match(protoSrc, /exec-proto-mobile-order/);
assert.match(protoSrc, /exec-proto-registry-map/);
assert.match(protoSrc, /exec-proto-finance-strip/);
assert.match(protoSrc, /exec-proto-header-actions/);
assert.match(protoSrc, /data-mobile-order/);
assert.match(protoSrc, /MetricCard/);
assert.match(protoSrc, /WidgetShell/);
assert.match(protoSrc, /DashboardGrid/);
assert.match(protoSrc, /DateRangeControl/);
assert.match(protoSrc, /IconButton/);
assert.match(protoSrc, /WidgetMenu/);
assert.match(protoSrc, /AreaChart/);
assert.match(protoSrc, /FunnelChart/);
assert.match(protoSrc, /DonutChart/);
assert.match(protoSrc, /BarChart/);
assert.match(protoSrc, /Sparkline/);
assert.match(protoSrc, /TimelineChart/);
assert.match(protoSrc, /ProgressChart/);
assert.match(protoSrc, /RightRail/);
assert.match(protoSrc, /kpiState === 'loading'/);
assert.match(protoSrc, /kpiState === 'empty'/);
assert.match(protoSrc, /kpiState === 'error'/);
assert.match(protoSrc, /chartState === 'empty'/);
assert.match(protoSrc, /chartState === 'error'/);
assert.match(protoSrc, /separationNote/);
assert.match(protoSrc, /aiReason/);
assert.match(protoSrc, /aiImpact/);
assert.match(protoSrc, /commsPermissionDenied/);
assert.match(protoSrc, /demoFinancePulse/);
assert.match(protoSrc, /tone:\s*'ai'|tone="ai"/);

// Separation: four independent widget ids present
for (const id of [
  'exec.tasks_approvals',
  'exec.calendar_deadlines',
  'exec.ai_decision',
  'exec.communications',
]) {
  assert.match(protoSrc, new RegExp(id.replace(/\./g, '\\.')));
}

// Sales and investors related but not merged
assert.match(protoSrc, /exec\.sales_funnel/);
assert.match(protoSrc, /exec\.investor_pulse/);
assert.match(protoSrc, /exec\.marketing_pulse/);
assert.match(protoSrc, /exec\.projects_progress/);

// Must not merge calendar/tasks/mail/AI into one card
assert.equal(protoSrc.includes('combined inbox'), false);
assert.equal(protoSrc.includes('CalendarTasksMailAi'), false);

// Mobile order sequence (D1C final)
const mobileBlock = protoSrc.slice(
  protoSrc.indexOf('const MOBILE_ORDER'),
  protoSrc.indexOf('};', protoSrc.indexOf('const MOBILE_ORDER')) + 2,
);
assert.match(mobileBlock, /'exec\.alerts': 1/);
assert.match(mobileBlock, /'exec\.kpi_cash': 2/);
assert.match(mobileBlock, /'exec\.ai_decision': 7/);
assert.match(mobileBlock, /'exec\.cash_trend': 8/);
assert.match(mobileBlock, /'exec\.tasks_approvals': 9/);
assert.match(mobileBlock, /'exec\.calendar_deadlines': 10/);
assert.match(mobileBlock, /'exec\.sales_funnel': 11/);
assert.match(mobileBlock, /'exec\.investor_pulse': 12/);
assert.match(mobileBlock, /'exec\.projects_progress': 13/);
assert.match(mobileBlock, /'exec\.marketing_pulse': 14/);
assert.match(mobileBlock, /'exec\.communications': 15/);

const demoSrc = read(demoData);
assert.match(demoSrc, /PROTOTYPE_DEMO_DATA_ONLY/);
assert.match(demoSrc, /NEVER import this module from production/i);
assert.match(demoSrc, /demoFinancePulse/);
assert.match(demoSrc, /liquidity/);
assert.match(demoSrc, /inflows/);
assert.match(demoSrc, /outflows/);
assert.match(demoSrc, /capital/);
assert.match(demoSrc, /reasonKey/);
assert.match(demoSrc, /impactKey/);
assert.match(demoSrc, /actionKey/);
assert.match(demoSrc, /demoMarketing/);
assert.match(demoSrc, /milestoneKey/);

// Must not call production executive APIs from prototype
assert.equal(protoSrc.includes('fetchExecutive'), false);
assert.equal(protoSrc.includes('lib/api/executive'), false);
assert.equal(demoSrc.includes('fetchExecutive'), false);
assert.equal(protoSrc.includes('useMutation'), false);
assert.equal(protoSrc.includes('apiFetch'), false);

// No duplicate executive-dashboard prototype routes under design-system
const dsRoot = join(webRoot, 'src/app/dashboard/admin/design-system');
const dsEntries = readdirSync(dsRoot, { withFileTypes: true });
const execDashDirs = dsEntries.filter(
  (e) => e.isDirectory() && e.name.includes('executive'),
);
assert.equal(execDashDirs.length, 1, 'expected exactly one executive prototype directory');
assert.equal(execDashDirs[0].name, 'executive-dashboard');

// Showcase D1C section + link
const showcase = read(
  'src/app/dashboard/admin/design-system/_components/design-system-showcase.tsx',
);
assert.match(showcase, /executive-dashboard/);
assert.match(showcase, /executivePrototypeLink/);
assert.match(showcase, /ds-d1c/);
assert.match(showcase, /ds-d1c-section/);
assert.match(showcase, /ds-d1c-registry-map/);
assert.match(showcase, /data-registry-id/);

// i18n TR + EN
const en = JSON.parse(readFileSync(join(webRoot, 'messages/en.json'), 'utf8'));
const tr = JSON.parse(readFileSync(join(webRoot, 'messages/tr.json'), 'utf8'));
const enP = en.designSystem.executivePrototype;
const trP = tr.designSystem.executivePrototype;
assert.ok(enP, 'en executivePrototype missing');
assert.ok(trP, 'tr executivePrototype missing');
assert.match(enP.title, /Executive overview/i);
assert.match(trP.title, /Yönetici özeti/i);
assert.match(enP.demoNotice, /prototype-only/i);
assert.match(trP.demoNotice, /prototype-only|prototip/i);
assert.equal(enP.kpiCash.length > 0, true);
assert.equal(trP.kpiCash.length > 0, true);
assert.equal(enP.separationNote.length > 0, true);
assert.equal(trP.separationNote.length > 0, true);
assert.equal(enP.aiReason.length > 0, true);
assert.equal(trP.aiReason.length > 0, true);
assert.equal(enP.aiImpact.length > 0, true);
assert.equal(trP.aiImpact.length > 0, true);
assert.equal(enP.investorsTitle.length > 0, true);
assert.equal(trP.investorsTitle.length > 0, true);
assert.equal(enP.marketingTitle.length > 0, true);
assert.equal(trP.marketingTitle.length > 0, true);
assert.equal(enP.commsPermissionDenied.length > 0, true);
assert.equal(trP.commsPermissionDenied.length > 0, true);
assert.equal(enP.responsiveDocBody.length > 0, true);
assert.equal(trP.responsiveDocBody.length > 0, true);
assert.equal(en.designSystem.executivePrototypeLink.length > 0, true);
assert.equal(tr.designSystem.executivePrototypeLink.length > 0, true);
assert.equal(en.designSystem.sections.d1c.length > 0, true);
assert.equal(tr.designSystem.sections.d1c.length > 0, true);
assert.equal(en.designSystem.d1cSectionBody.length > 0, true);
assert.equal(tr.designSystem.d1cSectionBody.length > 0, true);

// Docs
const docs = [
  'docs/design-system/executive-dashboard-current-state.md',
  'docs/design-system/executive-dashboard-information-architecture.md',
  'docs/design-system/executive-widget-inventory.md',
  'docs/design-system/executive-chart-matrix.md',
  'docs/design-system/executive-dashboard-grid.md',
  'docs/design-system/dashboard-customization-model.md',
  'docs/design-system/external-design-reference-plan.md',
  'docs/design-system/d1c-visual-review.md',
  'docs/design-system/executive-dashboard-visual-direction.md',
  'docs/design-system/d1c-visual-qa.md',
];
for (const doc of docs) {
  assert.equal(existsSync(join(repoRoot, doc)), true, `missing ${doc}`);
}

const review = readFileSync(join(repoRoot, 'docs/design-system/d1c-visual-review.md'), 'utf8');
assert.match(review, /Strengths/);
assert.match(review, /Weaknesses/);

const direction = readFileSync(
  join(repoRoot, 'docs/design-system/executive-dashboard-visual-direction.md'),
  'utf8',
);
assert.match(direction, /soft warm neutral|Soft warm neutral/i);
assert.match(direction, /AI Decision Center/);
assert.match(direction, /Mobile order/);

const inventory = readFileSync(
  join(repoRoot, 'docs/design-system/executive-widget-inventory.md'),
  'utf8',
);
assert.match(inventory, /exec\.alerts/);
assert.match(inventory, /Default selection/);
assert.match(inventory, /missing backend/i);

const grid = readFileSync(join(repoRoot, 'docs/design-system/executive-dashboard-grid.md'), 'utf8');
assert.match(grid, /Mobile \(1-col\)/);
assert.match(grid, /exec\.alerts/);

// Registry mapping ids present in prototype
for (const id of [
  'data-metric-card',
  'data-widget-shell',
  'chart-area',
  'primitive-date-range',
  'layout-dashboard-grid',
]) {
  assert.match(protoSrc, new RegExp(id));
}

console.log('executive-dashboard D1C prototype checks passed');
