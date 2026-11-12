/**
 * Phase 4 — database documents, demo-free portfolio KPIs, detail navigation.
 * Run: node --test src/app/dashboard/projects/_components/ds/__tests__/project-operational-phase4.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../../../../../');

function readRel(...parts) {
  return readFileSync(join(...parts), 'utf8');
}

const workspace = readRel(
  webSrc,
  'app/dashboard/projects/_components/ds/projects-detail-ds-workspace.tsx',
);
const detailModel = readRel(
  webSrc,
  'app/dashboard/projects/_components/ds/projects-detail-ds-model.ts',
);
const overview = readRel(
  webSrc,
  'app/dashboard/projects/_components/ds/projects-detail-overview-live.ts',
);
const portfolio = readRel(webSrc, 'app/dashboard/projects/_components/ds/projects-ds-model.ts');
const tabs = readRel(webSrc, 'lib/projects/project-detail-tabs.ts');
const page = readRel(webSrc, 'app/dashboard/projects/[projectId]/[tab]/page.tsx');
const en = JSON.parse(readRel(webSrc, '../messages/en.json'));
const tr = JSON.parse(readRel(webSrc, '../messages/tr.json'));

function documentsTab(source) {
  const start = source.indexOf('function DocumentsTab');
  const end = source.indexOf('function ', start + 1);
  return source.slice(start, end === -1 ? undefined : end);
}

describe('real project documents stay visible without Drive', () => {
  it('loads database documents inside DocumentsTab and does not require Drive assets', () => {
    const tab = documentsTab(workspace);
    assert.match(tab, /fetchProjectDocuments\(projectId/);
    assert.match(tab, /isOperationalProjectDocument/);
    assert.match(tab, /documentDownloadUrl\(doc\.id\)/);
    assert.match(tab, /data-testid="project-record-documents"/);
    assert.match(tab, /data-testid="project-drive-documents"/);
    assert.match(overview, /raw\.is_demo === true/);
    assert.match(overview, /archived_at/);
    assert.doesNotMatch(tab, /assets\.length === 0 \?[\s\S]{0,180}project-record-documents/);
  });
});

describe('portfolio KPIs exclude demo projects', () => {
  it('filters demo projects out of list, KPI, and right-rail derivations', () => {
    assert.match(portfolio, /export function operationalProjects/);
    assert.match(portfolio, /project\.is_demo !== true/);
    assert.match(portfolio, /return operationalProjects\(projects\)\.filter/);
    assert.match(portfolio, /const source = operationalProjects\(projects\)/);
    assert.doesNotMatch(portfolio, /delta: '\+12%'/);
    assert.doesNotMatch(portfolio, /delta: '\+8%'/);
  });
});

describe('detail navigation keeps routes and secondary access', () => {
  it('shows seven primary tabs and keeps legacy routes', () => {
    assert.match(
      detailModel,
      /PROJECT_DETAIL_NAV_TABS = \[\s*'overview',\s*'units',\s*'phases',\s*'investors',\s*'financial',\s*'construction',\s*'documents',\s*'tasks',\s*\]/,
    );
    for (const route of ['timeline', 'reports', 'ai-insights']) {
      assert.match(detailModel, new RegExp(`'${route}'`));
    }
    assert.match(detailModel, /financials: 'financial'/);
    assert.match(detailModel, /sales: 'units'/);
    assert.match(detailModel, /schedule: 'timeline'/);
    assert.match(page, /redirect\(projectDetailHref/);
    assert.match(tabs, /isProjectDetailDsTab\(value\) \|\| value in PROJECT_DETAIL_TAB_ALIASES/);
    assert.equal(en.projects.detail.tabs.units, 'Units & Sales');
    assert.equal(tr.projects.detail.tabs.units, 'Üniteler & Satış');
    assert.equal(tr.projects.detail.tabs.tasks, 'Görevler & Zaman Çizelgesi');
    assert.equal(tr.projects.detail.tabs.financial, 'Finans');
  });

  it('keeps Reports and AI reachable off the main navigation', () => {
    assert.match(workspace, /data-testid="project-detail-reports"/);
    assert.match(workspace, /projectDetailDsHref\(projectId, 'reports'\)/);
    assert.match(workspace, /data-testid="project-detail-ai"/);
    assert.match(workspace, /projectDetailDsHref\(projectId, 'ai-insights'\)/);
    assert.match(workspace, /resolvedTab === 'reports' \? <ReportsTab/);
    assert.match(workspace, /resolvedTab === 'ai-insights' \? <AiInsightsTab/);
    assert.match(workspace, /data-testid="project-work-tasks"/);
    assert.match(workspace, /data-testid="project-work-timeline"/);
    assert.match(workspace, /projectDetailDsHref\(projectId, 'tasks'\)/);
    assert.match(workspace, /projectDetailDsHref\(projectId, 'timeline'\)/);
    assert.match(workspace, /PROJECT_DETAIL_NAV_TABS\.filter\(\(id\) => id !== 'phases' \|\| usesPhases\)/);
    assert.match(workspace, /const phaseFilter = usesPhases \? phaseId : ''/);
    assert.match(workspace, /usesPhases && projectPhases\.length/);
    assert.match(workspace, /usesPhases && !controlled && phases\.length/);
    assert.match(workspace, /resolvedTab === 'phases' && !usesPhases \? 'overview' : resolvedTab/);
    const primaryNav = workspace.slice(
      workspace.indexOf('const tabItems'),
      workspace.indexOf('const onTabChange'),
    );
    assert.doesNotMatch(primaryNav, /reports|ai-insights/);
  });
});
