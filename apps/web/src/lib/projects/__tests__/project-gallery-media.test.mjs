import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

import {
  collectLinkedProjectMedia,
  isOperationalProjectMedia,
  projectMediaCategory,
} from '../project-gallery-media.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const overview = readFileSync(
  join(here, '../../../app/dashboard/projects/_components/ds/projects-detail-overview-live.ts'),
  'utf8',
);

function asset(overrides) {
  return {
    id: 'asset-1',
    filename: 'temple-exterior.jpg',
    content_type: 'image/jpeg',
    archived_at: null,
    sync_status: 'active',
    folder_category: '02_RENDER',
    tags: ['exterior'],
    linked_project_id: 'project-1',
    ...overrides,
  };
}

describe('project gallery media selection', () => {
  it('keeps an approved project render', () => {
    const item = asset({});
    assert.equal(isOperationalProjectMedia(item), true);
    assert.equal(projectMediaCategory(item), 'exterior');
  });

  it('rejects passport, agreement, and identity files', () => {
    assert.equal(
      isOperationalProjectMedia(asset({ filename: 'Can Mergen Pasaport.jpg', folder_category: '06_MEDIA' })),
      false,
    );
    assert.equal(
      isOperationalProjectMedia(asset({ filename: 'reservation-agreement.png', folder_category: '08_MARKETING' })),
      false,
    );
    assert.equal(
      isOperationalProjectMedia(asset({ filename: 'kimlik-on.jpg', tags: [] })),
      false,
    );
  });

  it('rejects document-folder files, archives, pdfs, and archived assets', () => {
    assert.equal(isOperationalProjectMedia(asset({ folder_category: '09_DOCUMENTS' })), false);
    assert.equal(isOperationalProjectMedia(asset({ folder_category: '00_PROJECT_INFO' })), false);
    assert.equal(isOperationalProjectMedia(asset({ folder_category: '10_ARCHIVE' })), false);
    assert.equal(isOperationalProjectMedia(asset({ content_type: 'application/pdf', filename: 'floor.pdf' })), false);
    assert.equal(isOperationalProjectMedia(asset({ archived_at: '2026-01-01' })), false);
    assert.equal(isOperationalProjectMedia(asset({ sync_status: 'missing' })), false);
  });

  it('maps floor plans and marketing folders', () => {
    assert.equal(projectMediaCategory(asset({ folder_category: '03_FLOOR_PLANS', filename: 'level-2.jpg', tags: [] })), 'floorPlan');
    assert.equal(projectMediaCategory(asset({ folder_category: '05_LOCATION', filename: 'site.jpg', tags: [] })), 'sitePlan');
    assert.equal(projectMediaCategory(asset({ folder_category: '08_MARKETING', filename: 'brochure-cover.jpg', tags: [] })), 'marketing');
  });

  it('does not admit a personal image that has no category or folder', () => {
    assert.equal(
      isOperationalProjectMedia(asset({
        filename: 'family-photo.jpg',
        folder_category: null,
        tags: [],
      })),
      false,
    );
    assert.equal(
      isOperationalProjectMedia(asset({
        filename: 'temple-exterior.jpg',
        folder_category: '',
        tags: null,
      })),
      false,
    );
  });

  it('keeps eligible project media beyond the first 100 linked assets', async () => {
    const documents = Array.from({ length: 100 }, (_, index) => asset({
      id: `doc-${index}`,
      filename: `passport-${index}.jpg`,
      folder_category: '09_DOCUMENTS',
      tags: [],
    }));
    const hero = asset({ id: 'hero-101', filename: 'temple-hero.jpg' });
    const pages = [];
    const selected = await collectLinkedProjectMedia(async ({ page }) => {
      pages.push(page);
      if (page === 1) return { items: documents, total: 101 };
      return { items: [hero], total: 101 };
    }, 'project-1');
    assert.deepEqual(pages, [1, 2]);
    assert.deepEqual(selected.map((item) => item.id), ['hero-101']);
  });

  it('does not use the documents table as a gallery source', () => {
    assert.doesNotMatch(overview, /documentPreviewUrl/);
    assert.match(overview, /isOperationalProjectMedia/);
    assert.match(overview, /getCreativeStudioMediaContentUrl/);
  });
});
