/**
 * Location refresh click contract.
 * Run: node --test src/lib/projects/__tests__/location-refresh-action.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  createLocationRefreshController,
  locationReadPath,
  locationRefreshPath,
} from '../location-refresh-action.mjs';

const PROJECT_ID = 'd08ffa5a-bb69-4eaf-976c-b8ceae218e41';
const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

describe('location refresh request', () => {
  it('posts once to the project UUID refresh path', async () => {
    const posts = [];
    const reads = [];
    const events = [];
    const pending = deferred();
    const controller = createLocationRefreshController({
      projectId: PROJECT_ID,
      intervalMs: 1000,
      post: (path) => {
        posts.push(path);
        return pending.promise;
      },
      read: async (path) => {
        reads.push(path);
        return { status: 'pending' };
      },
    });
    controller.subscribe((event) => events.push(event));

    const first = controller.click();
    const second = await controller.click();
    assert.equal(posts.length, 1);
    assert.equal(posts[0], locationRefreshPath(PROJECT_ID));
    assert.equal(posts[0], `/projects/${PROJECT_ID}/location-intelligence/refresh`);
    assert.equal(second.posted, false);
    assert.equal(reads.length, 0);
    assert.equal(events[0].type, 'status');
    assert.equal(events[0].status, 'working');

    pending.resolve({ status: 'disabled' });
    const finished = await first;
    assert.equal(finished.posted, true);
    assert.equal(finished.status, 'disabled');
    assert.equal(posts.length, 1);
    assert.equal(reads.length, 0);
    assert.equal(events.at(-1).status, 'disabled');
    controller.stop();
  });

  it('renders queued, already_queued, disabled, and error feedback', async () => {
    for (const status of ['queued', 'already_queued', 'disabled']) {
      const events = [];
      const reads = [];
      const controller = createLocationRefreshController({
        projectId: PROJECT_ID,
        intervalMs: 5000,
        post: async () => ({ status }),
        read: async (path) => {
          reads.push(path);
          return { status: 'success' };
        },
      });
      controller.subscribe((event) => events.push(event));
      const result = await controller.click();
      assert.equal(result.posted, true);
      assert.equal(result.status, status);
      assert.equal(events.some((event) => event.type === 'status' && event.status === status), true);
      if (status === 'disabled') assert.equal(reads.length, 0);
      if (status !== 'disabled') {
        await new Promise((resolve) => setTimeout(resolve, 20));
        assert.equal(reads[0], locationReadPath(PROJECT_ID));
        assert.equal(reads[0].endsWith('/refresh'), false);
      }
      controller.stop();
    }

    const errors = [];
    const failed = createLocationRefreshController({
      projectId: PROJECT_ID,
      post: async () => {
        throw new Error('Request failed with status 403');
      },
      read: async () => {
        throw new Error('read should not run');
      },
    });
    failed.subscribe((event) => errors.push(event));
    const result = await failed.click();
    assert.equal(result.posted, true);
    assert.equal(result.status, 'error');
    assert.equal(result.error, 'Request failed with status 403');
    assert.equal(errors.at(-1).status, 'error');
    assert.equal(errors.at(-1).error, 'Request failed with status 403');
  });

  it('keeps the overview read on GET and never calls an external provider', () => {
    const action = read('lib/projects/location-refresh-action.mjs');
    const projects = read('lib/api/projects.ts');
    const workspace = read('app/dashboard/projects/_components/ds/projects-detail-ds-workspace.tsx');
    const location = read('app/dashboard/projects/_components/ds/projects-detail-location.tsx');
    const twin = read('app/dashboard/projects/_components/ds/projects-detail-digital-twin.tsx');
    const page = read('app/dashboard/projects/[projectId]/[tab]/page.tsx');

    assert.match(projects, /method: 'POST'/);
    assert.match(projects, /body: '\{\}'/);
    assert.match(projects, /locationRefreshPath\(projectId\)/);
    assert.match(projects, /locationReadPath\(projectId\)/);
    assert.doesNotMatch(
      projects.slice(projects.indexOf('fetchProjectLocationIntelligence'), projects.indexOf('refreshProjectLocationIntelligence')),
      /method:\s*'POST'/,
    );

    assert.match(workspace, /refreshProjectLocationIntelligence\(projectId\)/);
    assert.match(workspace, /fetchProjectLocationIntelligence\(projectId\)/);
    assert.match(workspace, /controller\.click\(\)/);
    assert.match(workspace, /onRefreshLocation=\{refreshLocation\}/);
    assert.match(location, /data-testid="project-location-refresh"/);
    assert.match(location, /onRefresh\(\)/);
    assert.match(location, /location\.refreshState\.\$\{refreshState\}/);
    assert.match(location, /refreshError/);
    assert.match(twin, /onRefresh=\{onRefreshLocation\}/);
    assert.match(page, /projectId=\{projectId\}/);
    assert.doesNotMatch(workspace, /project\.code/);
    assert.doesNotMatch(workspace, /bf605fe2-cfea-43fa-8d92-1f91a2b6f04f/);
    assert.doesNotMatch(workspace, /3220-16TH-NW/);

    const sources = [action, projects, workspace, location, twin];
    for (const source of sources) {
      assert.doesNotMatch(source, /maps\.googleapis|api\.walkscore|api\.openai|generativelanguage|walkscore\.com/i);
    }
  });
});
