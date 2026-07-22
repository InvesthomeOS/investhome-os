/**
 * Design Sprint D1D production executive dashboard contract checks.
 * Run: node src/components/design-system/__tests__/executive-dashboard-production.test.mjs
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

const docs = [
  'docs/design-system/d1d-production-route-mapping.md',
  'docs/design-system/d1d-production-data-map.md',
  'docs/design-system/d1d-production-widget-selection.md',
  'docs/design-system/d1d-dashboard-performance.md',
  'docs/design-system/d1d-production-migration.md',
  'docs/design-system/d1d-production-verification.md',
];

for (const doc of docs) {
  assert.equal(existsSync(join(repoRoot, doc)), true, `missing ${doc}`);
}

const prodDash =
  'src/app/dashboard/executive/_components/production-dashboard/production-executive-dashboard.tsx';
const workspace = 'src/app/dashboard/executive/_components/executive-workspace.tsx';
const analytics =
  'src/app/dashboard/executive/_components/production-dashboard/executive-ui-analytics.ts';
const protoDemo =
  'src/app/dashboard/admin/design-system/executive-dashboard/_components/prototype-demo-data.ts';
const protoPage = 'src/app/dashboard/admin/design-system/executive-dashboard/page.tsx';

assert.equal(existsSync(join(webRoot, prodDash)), true, 'production dashboard missing');
assert.equal(existsSync(join(webRoot, workspace)), true, 'workspace missing');
assert.equal(existsSync(join(webRoot, analytics)), true, 'analytics helper missing');
assert.equal(existsSync(join(webRoot, protoDemo)), true, 'prototype demo must remain');
assert.equal(existsSync(join(webRoot, protoPage)), true, 'prototype route must remain');

const prodSrc = read(prodDash);
const workspaceSrc = read(workspace);
const analyticsSrc = read(analytics);
const css = read('src/app/design-system.css');
const en = read('messages/en.json');
const tr = read('messages/tr.json');

assert.match(prodSrc, /data-testid="executive-dashboard-production"/);
assert.match(prodSrc, /data-sprint="D1D"/);
assert.match(prodSrc, /exec-prod-section-alerts/);
assert.match(prodSrc, /exec-prod-section-kpis/);
assert.match(prodSrc, /exec-prod-section-decision-finance/);
assert.match(prodSrc, /exec-prod-section-work/);
assert.match(prodSrc, /exec-prod-tasks-widget/);
assert.match(prodSrc, /exec-prod-calendar-widget/);
assert.match(prodSrc, /exec-prod-ai-widget/);
assert.match(prodSrc, /exec-prod-comms-widget/);
assert.match(prodSrc, /exec-prod-sales-widget/);
assert.match(prodSrc, /exec-prod-investors-widget/);
assert.match(prodSrc, /exec-prod-projects-widget/);
assert.match(prodSrc, /exec-prod-marketing-widget/);
assert.match(prodSrc, /MetricCard/);
assert.match(prodSrc, /WidgetShell/);
assert.match(prodSrc, /DashboardGrid/);
assert.match(prodSrc, /AreaChart/);
assert.match(prodSrc, /FunnelChart/);
assert.match(prodSrc, /TimelineChart/);
assert.match(prodSrc, /statusSystemRecs/);
assert.match(prodSrc, /separationNote/);
assert.match(prodSrc, /cashHistoricalGap/);
assert.match(prodSrc, /projectsProgressUnavailable/);
assert.match(prodSrc, /commsPermissionDenied/);
assert.doesNotMatch(prodSrc, /prototype-demo-data/);
assert.doesNotMatch(prodSrc, /demoKpis|demoCashTrend|demoAiItems/);

assert.match(workspaceSrc, /ProductionExecutiveDashboard/);
assert.match(workspaceSrc, /viewParam !== 'legacy'/);
assert.match(workspaceSrc, /view.*legacy|legacy/);
assert.match(workspaceSrc, /canViewExecutive/);
assert.match(workspaceSrc, /data-testid="executive-dashboard-legacy"/);
assert.doesNotMatch(workspaceSrc, /isFeatureEnabled/);
assert.doesNotMatch(workspaceSrc, /fetchFeatureFlags/);
assert.doesNotMatch(workspaceSrc, /prototype-demo-data/);
assert.doesNotMatch(workspaceSrc, /from ['\"].*executive-dashboard-prototype/);
// Unknown / missing view must default to production (not legacy)
assert.match(workspaceSrc, /useProductionLayout = viewParam !== 'legacy'/);

assert.match(analyticsSrc, /trackExecutiveUiEvent/);
assert.match(analyticsSrc, /executive_dashboard_view/);
assert.match(analyticsSrc, /SENSITIVE_KEYS/);

assert.match(css, /\.ds-exec-prod/);
assert.match(css, /\.ds-exec-prod-kpi-strip/);
assert.match(css, /prefers-reduced-motion/);

assert.match(en, /"production"/);
assert.match(en, /AI Decision Center/);
assert.match(tr, /"production"/);
assert.match(tr, /AI Karar Merkezi/);

const protoPageSrc = read(protoPage);
assert.match(protoPageSrc, /prototype ONLY/i);
assert.match(protoPageSrc, /not the production executive/i);

const routeMap = readRepo('docs/design-system/d1d-production-route-mapping.md');
assert.match(routeMap, /\/dashboard\/executive/);
assert.match(routeMap, /executive:view/);
assert.match(routeMap, /executive_dashboard/);

const dataMap = readRepo('docs/design-system/d1d-production-data-map.md');
assert.match(dataMap, /cash_flow_trend/);
assert.match(dataMap, /Missing endpoint|Unsupported/);

const widgetSel = readRepo('docs/design-system/d1d-production-widget-selection.md');
assert.match(widgetSel, /exec\.alerts/);
assert.match(widgetSel, /exec\.communications/);

// touch_session P11 must remain intact
const sessionSvc = readRepo('apps/api/src/investhome_api/services/session_service.py');
assert.match(sessionSvc, /def touch_session/);
assert.match(sessionSvc, /_TOUCH_MIN_INTERVAL/);
assert.match(sessionSvc, /SessionLocal/);

console.log('executive-dashboard-production.test.mjs: ok');
