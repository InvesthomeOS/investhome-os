/**
 * Project hero/gallery selection.
 * Operational documents (passports, agreements, IDs) are never project media.
 */

export const PROJECT_MEDIA_FOLDER_CATEGORIES = [
  '01_BRAND',
  '02_RENDER',
  '03_FLOOR_PLANS',
  '04_UNIT_PLANS',
  '05_LOCATION',
  '06_MEDIA',
  '07_CATALOG',
  '08_MARKETING',
];

const PROJECT_MEDIA_FOLDERS = new Set(PROJECT_MEDIA_FOLDER_CATEGORIES);

const BLOCKED_FOLDERS = new Set(['00_PROJECT_INFO', '09_DOCUMENTS', '10_ARCHIVE']);

const BLOCKED_FOLDER_TEXT = /document|investor|contract|agreement|reservation|passport|pasaport|identity|kimlik|legal|finance|project[\s_-]?info|archive/i;

const PERSONAL_DOCUMENT = /passport|pasaport|kimlik|identity|national id|agreement|sozlesme|sözleşme|reservation|rezervasyon|investor|müşteri|musteri|customer|contract|legal|finance/i;

const GALLERY_PAGE_SIZE = 100;
const GALLERY_MAX_PAGES = 100;

const EXPLICIT_TAGS = [
  ['floorPlan', /^floor[\s-]?plan$|^floorplan$/i],
  ['sitePlan', /^site[\s-]?plan$|^siteplan$/i],
  ['rendering', /^rendering$|^render$/i],
  ['exterior', /^exterior$/i],
  ['interior', /^interior$/i],
  ['drone', /^drone$/i],
  ['street', /^street$/i],
  ['marketing', /^marketing$/i],
  ['construction', /^construction$/i],
  ['cover', /^cover$/i],
];

const HERO_CATEGORY_ORDER = [
  'cover',
  'exterior',
  'rendering',
  'interior',
  'marketing',
  'street',
  'sitePlan',
  'construction',
  'drone',
  'floorPlan',
];

function folderKey(asset) {
  return typeof asset.folder_category === 'string' ? asset.folder_category.trim() : '';
}

function tagValues(asset) {
  if (!Array.isArray(asset.tags)) return [];
  return asset.tags.map((tag) => String(tag).trim()).filter(Boolean);
}

function explicitTagCategory(asset) {
  for (const tag of tagValues(asset)) {
    for (const [category, pattern] of EXPLICIT_TAGS) {
      if (pattern.test(tag)) return category;
    }
  }
  return null;
}

function isBlockedFolder(folder) {
  if (!folder) return false;
  if (BLOCKED_FOLDERS.has(folder)) return true;
  return BLOCKED_FOLDER_TEXT.test(folder);
}

export function isOperationalProjectMedia(asset) {
  if (!asset || asset.archived_at != null) return false;
  const sync = asset.sync_status;
  if (sync === 'missing' || sync === 'error') return false;
  const type = String(asset.content_type || '').toLowerCase();
  if (!type.startsWith('image/') && !type.startsWith('video/')) return false;
  const folder = folderKey(asset);
  if (isBlockedFolder(folder)) return false;
  const folderAllowed = PROJECT_MEDIA_FOLDERS.has(folder);
  const tagCategory = explicitTagCategory(asset);
  if (!folderAllowed && !tagCategory) return false;
  const label = `${asset.filename || ''} ${tagValues(asset).join(' ')}`;
  if (PERSONAL_DOCUMENT.test(label)) return false;
  return true;
}

export async function collectLinkedProjectMedia(fetchPage, projectId) {
  const accepted = [];
  let page = 1;
  let total = 0;
  do {
    const res = await fetchPage({
      linked_project_id: projectId,
      include_archived: false,
      page,
      page_size: GALLERY_PAGE_SIZE,
    });
    const items = Array.isArray(res?.items) ? res.items : [];
    total = Number(res?.total ?? items.length);
    for (const item of items) {
      if (!item || item.linked_project_id !== projectId || item.archived_at != null) continue;
      if (isOperationalProjectMedia(item)) accepted.push(item);
    }
    if (items.length === 0) break;
    page += 1;
  } while ((page - 1) * GALLERY_PAGE_SIZE < total && page <= GALLERY_MAX_PAGES);
  return accepted;
}

export function projectMediaCategory(asset) {
  const tags = Array.isArray(asset.tags) ? asset.tags.join(' ') : '';
  const blob = `${asset.folder_category || ''} ${asset.filename || ''} ${tags}`.toLowerCase();
  const folder = asset.folder_category || '';
  if (folder === '03_FLOOR_PLANS' || folder === '04_UNIT_PLANS' || blob.includes('floor plan') || blob.includes('floorplan')) {
    return 'floorPlan';
  }
  if (folder === '05_LOCATION' || blob.includes('site plan') || blob.includes('siteplan')) return 'sitePlan';
  if (blob.includes('interior')) return 'interior';
  if (blob.includes('exterior')) return 'exterior';
  if (blob.includes('drone')) return 'drone';
  if (blob.includes('street')) return 'street';
  if (blob.includes('construction')) return 'construction';
  if (folder === '08_MARKETING' || folder === '01_BRAND' || folder === '07_CATALOG' || blob.includes('marketing')) {
    return 'marketing';
  }
  if (folder === '02_RENDER' || blob.includes('render')) return 'rendering';
  return 'cover';
}

export function heroRank(category) {
  const index = HERO_CATEGORY_ORDER.indexOf(category);
  return index === -1 ? HERO_CATEGORY_ORDER.length : index;
}
