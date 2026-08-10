/**
 * Builder media persistence via Creative Studio Document API.
 * Run: node --test src/app/workspaces/creative-studio/_components/__tests__/builder-media-persistence.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const componentsDir = join(here, '..');
const studioDir = join(here, '../..');

function read(rel) {
  return readFileSync(join(componentsDir, rel), 'utf8');
}

const SAMPLE_UUID = '11111111-1111-4111-8111-111111111111';
const DEMO_ASSET_ID_RE = /^a\d+$/i;
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isDemoAssetId(id) {
  return Boolean(id && DEMO_ASSET_ID_RE.test(String(id).trim()));
}
function isMediaAssetUuid(id) {
  if (!id) return false;
  const trimmed = String(id).trim();
  if (isDemoAssetId(trimmed)) return false;
  return UUID_RE.test(trimmed);
}
function isEphemeralDisplayUrl(url) {
  if (!url) return false;
  const lower = String(url).trim().toLowerCase();
  return lower.startsWith('blob:') || lower.startsWith('object:') || lower.startsWith('filesystem:');
}
function isPersistableUrl(url) {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();
  if (!trimmed) return false;
  if (isEphemeralDisplayUrl(trimmed)) return false;
  return true;
}
function parseImageRef(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const assetRaw =
    typeof raw.asset_id === 'string' ? raw.asset_id : typeof raw.assetId === 'string' ? raw.assetId : null;
  const safeAssetId = assetRaw && isMediaAssetUuid(assetRaw) ? assetRaw.trim() : null;
  const urlRaw = typeof raw.url === 'string' ? raw.url : typeof raw.src === 'string' ? raw.src : null;
  const url = isPersistableUrl(urlRaw) ? urlRaw.trim() : null;
  if (!safeAssetId && !url) return null;
  return {
    asset_id: safeAssetId,
    url,
    alt: typeof raw.alt === 'string' ? raw.alt : null,
    focal: typeof raw.focal === 'string' ? raw.focal : null,
    crop: typeof raw.crop === 'string' ? raw.crop : null,
    role: typeof raw.role === 'string' ? raw.role : null,
  };
}
function sanitizeImageRef(ref) {
  if (!ref) return null;
  const asset_id = ref.asset_id && isMediaAssetUuid(ref.asset_id) ? ref.asset_id : null;
  const url = isPersistableUrl(ref.url) ? ref.url.trim() : null;
  if (!asset_id && !url) return null;
  return { asset_id, url, alt: ref.alt ?? null, focal: ref.focal ?? null, crop: ref.crop ?? null, role: ref.role ?? null };
}
function serializeImageRef(ref) {
  const clean = sanitizeImageRef(ref);
  if (!clean) return null;
  const out = { asset_id: clean.asset_id };
  if (clean.url) out.url = clean.url;
  if (clean.alt) out.alt = clean.alt;
  if (clean.focal) out.focal = clean.focal;
  if (clean.crop) out.crop = clean.crop;
  if (clean.role) out.role = clean.role;
  return out;
}
function imageRefFromLegacyUrl(url, role) {
  if (!isPersistableUrl(url)) return null;
  return { asset_id: null, url: url.trim(), alt: null, focal: null, crop: null, role: role ?? null };
}

const BUILDER_MEDIA_DOCUMENT_TYPES = [
  'landing',
  'blog',
  'email',
  'proposal',
  'presentation',
  'social',
];
function isBuilderMediaDocumentType(value) {
  return BUILDER_MEDIA_DOCUMENT_TYPES.includes(value);
}
function normalizeBuilderCoverFields(body) {
  const cover =
    parseImageRef(body.coverImage) ||
    parseImageRef(body.heroImage) ||
    (typeof body.coverUrl === 'string' ? imageRefFromLegacyUrl(body.coverUrl, 'cover') : null) ||
    (typeof body.heroCoverOverride === 'string'
      ? imageRefFromLegacyUrl(body.heroCoverOverride, 'cover')
      : null);
  const galleryFromRefs = Array.isArray(body.galleryImages)
    ? body.galleryImages.map((item) => parseImageRef(item)).filter(Boolean)
    : [];
  const galleryFromLegacy = Array.isArray(body.galleryOverride)
    ? body.galleryOverride
        .filter((u) => typeof u === 'string')
        .map((u) => imageRefFromLegacyUrl(u, 'gallery'))
        .filter(Boolean)
    : [];
  const galleryFromUrls = Array.isArray(body.galleryUrls)
    ? body.galleryUrls
        .filter((u) => typeof u === 'string')
        .map((u) => imageRefFromLegacyUrl(u, 'gallery'))
        .filter(Boolean)
    : [];
  return {
    coverImage: cover,
    galleryImages: galleryFromRefs.length
      ? galleryFromRefs
      : galleryFromLegacy.length
        ? galleryFromLegacy
        : galleryFromUrls,
  };
}
function serializeBuilderMediaDraft(input) {
  const coverSerialized = serializeImageRef(input.coverImage);
  const gallerySerialized = (input.galleryImages ?? [])
    .map((ref) => serializeImageRef(ref))
    .filter(Boolean);
  return {
    schemaVersion: 1,
    documentType: input.documentType,
    linkedProjectId: input.linkedProjectId,
    coverImage: coverSerialized,
    galleryImages: gallerySerialized,
    savedAt: Date.now(),
  };
}
function deserializeBuilderMediaDraft(raw, fallbackType) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw;
  const { coverImage, galleryImages } = normalizeBuilderCoverFields(body);
  const typeRaw = typeof body.documentType === 'string' ? body.documentType : fallbackType;
  const documentType = isBuilderMediaDocumentType(typeRaw) ? typeRaw : fallbackType;
  const keys = Object.keys(body);
  if (keys.length === 0) return null;
  if (!coverImage && galleryImages.length === 0 && keys.length <= 2) {
    const onlyMeta = keys.every((k) =>
      ['schemaVersion', 'documentType', 'linkedProjectId', 'savedAt'].includes(k),
    );
    if (onlyMeta) return null;
  }
  return {
    schemaVersion: 1,
    documentType,
    linkedProjectId: typeof body.linkedProjectId === 'string' ? body.linkedProjectId : null,
    coverImage,
    galleryImages,
    savedAt: typeof body.savedAt === 'number' ? body.savedAt : undefined,
  };
}
function assertSafeBuilderMediaDraft(draft) {
  const blob = JSON.stringify(draft);
  if (/blob:/i.test(blob) || /filesystem:/i.test(blob) || /object:/i.test(blob)) {
    return { ok: false, reason: 'ephemeral url' };
  }
  if (/drive\.google\.com/i.test(blob) || /\/file\/d\//i.test(blob)) {
    return { ok: false, reason: 'drive path' };
  }
  const cover = draft.coverImage;
  if (cover && typeof cover === 'object') {
    if ('drive_file_id' in cover || 'driveFileId' in cover || 'path' in cover) {
      return { ok: false, reason: 'drive identity field' };
    }
  }
  return { ok: true };
}

async function resolveCreativeStudioDocument(deps) {
  const listed = await deps.listDocuments(deps.csProjectId);
  const existing = listed.items.find(
    (item) => item.document_type === deps.documentType && item.archived_at == null,
  );
  if (existing) {
    const document = await deps.getDocument(existing.id);
    return { document, created: false };
  }
  const document = await deps.createDocument(deps.csProjectId, {
    title: deps.documentTitle.trim() || deps.documentType,
    document_type: deps.documentType,
    status: 'draft',
    draft_body_json: {},
  });
  return { document, created: true };
}

describe('source modules exist', () => {
  it('ships persistence + session + document hook', () => {
    assert.equal(existsSync(join(componentsDir, 'builder-media-persistence.ts')), true);
    assert.equal(existsSync(join(componentsDir, 'cs-document-session.ts')), true);
    assert.equal(existsSync(join(componentsDir, 'use-builder-document.ts')), true);
  });

  it('builders wire useBuilderDocument + useBuilderCoverAsset', () => {
    for (const rel of [
      'landing-page-builder/landing-page-builder-workspace.tsx',
      'blog-builder/blog-builder-workspace.tsx',
      'email-builder/email-builder-workspace.tsx',
      'proposal-builder/proposal-builder-workspace.tsx',
      'presentation-builder/presentation-builder-workspace.tsx',
      'social-media-builder/social-media-builder-workspace.tsx',
    ]) {
      const src = readFileSync(join(studioDir, rel), 'utf8');
      assert.match(src, /useBuilderDocument/);
      assert.match(src, /useBuilderCoverAsset/);
      assert.match(src, /hydrateMedia/);
      assert.match(src, /saveCreativeStudioDraft|saveDraft/);
    }
  });

  it('Website Builder session still resolves website documents', () => {
    const src = readFileSync(
      join(studioDir, 'website-builder/website-builder-session.ts'),
      'utf8',
    );
    assert.match(src, /resolveCreativeStudioDocument/);
    assert.match(src, /documentType:\s*'website'/);
    assert.match(src, /resolveWebsiteDocument/);
  });
});

for (const documentType of BUILDER_MEDIA_DOCUMENT_TYPES) {
  describe(`builder media draft (${documentType})`, () => {
    it('select asset ? save ? reload restores Asset ID', () => {
      const saved = serializeBuilderMediaDraft({
        documentType,
        linkedProjectId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        coverImage: { asset_id: SAMPLE_UUID, url: null, alt: 'Hero', role: 'cover' },
        galleryImages:
          documentType === 'landing'
            ? [{ asset_id: SAMPLE_UUID, url: null, alt: 'G', role: 'gallery' }]
            : [],
      });
      const loaded = deserializeBuilderMediaDraft(saved, documentType);
      assert.equal(loaded.coverImage.asset_id, SAMPLE_UUID);
      if (documentType === 'landing') {
        assert.equal(loaded.galleryImages[0].asset_id, SAMPLE_UUID);
      }
    });

    it('session reset simulation re-deserializes same Asset ID', () => {
      const body = serializeBuilderMediaDraft({
        documentType,
        linkedProjectId: null,
        coverImage: { asset_id: SAMPLE_UUID },
      });
      const first = deserializeBuilderMediaDraft(body, documentType);
      const second = deserializeBuilderMediaDraft(
        JSON.parse(JSON.stringify(body)),
        documentType,
      );
      assert.equal(first.coverImage.asset_id, second.coverImage.asset_id);
    });

    it('missing asset keeps ref safely', () => {
      const loaded = deserializeBuilderMediaDraft(
        {
          documentType,
          coverImage: { asset_id: SAMPLE_UUID },
        },
        documentType,
      );
      assert.equal(loaded.coverImage.asset_id, SAMPLE_UUID);
      assert.equal(loaded.coverImage.url ?? null, null);
    });

    it('legacy URL draft opens', () => {
      const loaded = deserializeBuilderMediaDraft(
        {
          coverUrl: 'https://images.unsplash.com/photo-1?auto=format',
        },
        documentType,
      );
      assert.equal(loaded.coverImage.asset_id, null);
      assert.match(loaded.coverImage.url, /^https:\/\//);
    });

    it('legacy replace ? Asset ID format', () => {
      const legacy = deserializeBuilderMediaDraft(
        { coverImage: { url: 'https://images.unsplash.com/legacy.jpg' } },
        documentType,
      );
      const replaced = serializeBuilderMediaDraft({
        documentType,
        linkedProjectId: null,
        coverImage: { asset_id: SAMPLE_UUID, alt: 'ML' },
      });
      assert.equal(legacy.coverImage.asset_id, null);
      assert.equal(replaced.coverImage.asset_id, SAMPLE_UUID);
      assert.equal(Object.prototype.hasOwnProperty.call(replaced.coverImage, 'url'), false);
    });

    it('rejects Drive path / blob in draft safety check', () => {
      const ok = assertSafeBuilderMediaDraft(
        serializeBuilderMediaDraft({
          documentType,
          linkedProjectId: null,
          coverImage: { asset_id: SAMPLE_UUID },
        }),
      );
      assert.equal(ok.ok, true);
      const blob = assertSafeBuilderMediaDraft({
        coverImage: { asset_id: null, url: 'blob:http://localhost/x' },
      });
      assert.equal(blob.ok, false);
      const drive = assertSafeBuilderMediaDraft({
        coverImage: { asset_id: null, url: 'https://drive.google.com/file/d/abc/view' },
      });
      assert.equal(drive.ok, false);
    });

    it('resolves document by type without duplicates', async () => {
      let createCalls = 0;
      const listed = {
        id: 'doc-1',
        document_type: documentType,
        archived_at: null,
        draft_body_json: { coverImage: { asset_id: SAMPLE_UUID } },
      };
      const first = await resolveCreativeStudioDocument({
        csProjectId: 'cs-1',
        documentType,
        documentTitle: 'Demo',
        listDocuments: async () => ({ items: [listed], total: 1 }),
        getDocument: async (id) => ({ ...listed, id }),
        createDocument: async () => {
          createCalls += 1;
          throw new Error('should not create');
        },
      });
      assert.equal(first.created, false);
      assert.equal(createCalls, 0);
    });
  });
}

describe('source contracts', () => {
  it('serializeImageRef never keeps blob urls', () => {
    const src = read('cs-image-ref.ts');
    assert.match(src, /isEphemeralDisplayUrl/);
    assert.match(src, /serializeImageRef/);
  });

  it('builder-media-persistence exports expected API', () => {
    const src = read('builder-media-persistence.ts');
    assert.match(src, /serializeBuilderMediaDraft/);
    assert.match(src, /deserializeBuilderMediaDraft/);
    assert.match(src, /assertSafeBuilderMediaDraft/);
  });
});
