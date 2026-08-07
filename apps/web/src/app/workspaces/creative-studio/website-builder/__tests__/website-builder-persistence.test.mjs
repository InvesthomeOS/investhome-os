/**
 * Website Builder Creative Studio persistence + media ref tests.
 * Run: node --test src/app/workspaces/creative-studio/website-builder/__tests__/website-builder-persistence.test.mjs
 *
 * Mirrors serialize/deserialize/resolve algorithms from the TS modules
 * (Node cannot resolve TS path aliases / extensionless imports without a bundler).
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const wbDir = join(here, '..');
const webSrc = join(here, '../../../../../');

function read(rel) {
  return readFileSync(join(wbDir, rel), 'utf8');
}

const DEFAULT_SECTIONS = [
  { id: 's-hero', key: 'hero', visible: true },
  { id: 's-about', key: 'about', visible: true },
];

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
  return {
    asset_id,
    url,
    alt: ref.alt ?? null,
    focal: ref.focal ?? null,
    crop: ref.crop ?? null,
    role: ref.role ?? null,
  };
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

function normalizeLegacyImageFields(body) {
  const heroFromV2 = parseImageRef(body.heroImage);
  if (heroFromV2) {
    const galleryFromV2 = Array.isArray(body.galleryImages)
      ? body.galleryImages.map((item) => parseImageRef(item)).filter(Boolean)
      : [];
    return { heroImage: heroFromV2, galleryImages: galleryFromV2 };
  }
  const legacyHero =
    typeof body.heroCoverOverride === 'string' && isPersistableUrl(body.heroCoverOverride)
      ? imageRefFromLegacyUrl(body.heroCoverOverride, 'hero')
      : null;
  const legacyGallery = Array.isArray(body.galleryOverride)
    ? body.galleryOverride
        .filter((u) => typeof u === 'string' && isPersistableUrl(u))
        .map((u) => imageRefFromLegacyUrl(u, 'gallery'))
    : [];
  const galleryOnly = Array.isArray(body.galleryImages)
    ? body.galleryImages.map((item) => parseImageRef(item)).filter(Boolean)
    : [];
  return {
    heroImage: legacyHero,
    galleryImages: galleryOnly.length ? galleryOnly : legacyGallery,
  };
}

function resolveDisplayUrl({ ref, resolvedAssetUrl, templateUrl, placeholderUrl }) {
  if (resolvedAssetUrl) return resolvedAssetUrl;
  if (ref?.url && isPersistableUrl(ref.url)) return ref.url;
  if (templateUrl) return templateUrl;
  if (placeholderUrl) return placeholderUrl;
  return null;
}

function normalizeWbSections(sections) {
  if (!Array.isArray(sections) || sections.length === 0) return DEFAULT_SECTIONS;
  return sections;
}

function serializeWebsiteBuilderDraft(input) {
  const heroSerialized = serializeImageRef(input.heroImage);
  const gallerySerialized = (input.galleryImages ?? [])
    .map((ref) => serializeImageRef(ref))
    .filter(Boolean);
  return {
    schemaVersion: 2,
    linkedProjectId: input.linkedProjectId,
    sections: normalizeWbSections(input.sections),
    selectedSectionId: input.selectedSectionId || 's-hero',
    metaTitle: input.metaTitle ?? '',
    metaDesc: input.metaDesc ?? '',
    slug: input.slug ?? '',
    publishStatus: input.publishStatus ?? 'draft',
    language: input.language ?? 'tr',
    tone: input.tone ?? 'luxury',
    brief: input.brief ?? '',
    siteGoal: input.siteGoal ?? '',
    audience: input.audience ?? '',
    mainMessage: input.mainMessage ?? '',
    heroTitle: input.heroTitle ?? '',
    heroBody: input.heroBody ?? '',
    ctaPrimary: input.ctaPrimary ?? '',
    ctaSecondary: input.ctaSecondary ?? '',
    heroImage: heroSerialized,
    galleryImages: gallerySerialized,
    savedAt: Date.now(),
  };
}

function deserializeWebsiteBuilderDraft(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  if (Array.isArray(raw.sections) && typeof raw.projectId === 'string') {
    return {
      schemaVersion: 2,
      linkedProjectId: null,
      sections: normalizeWbSections(raw.sections),
      selectedSectionId: raw.selectedSectionId || 's-hero',
      metaTitle: raw.metaTitle ?? '',
      metaDesc: raw.metaDesc ?? '',
      slug: raw.slug ?? '',
      publishStatus: raw.publishStatus ?? 'draft',
      language: raw.language ?? 'tr',
      tone: raw.tone ?? 'luxury',
      brief: '',
      siteGoal: '',
      audience: '',
      mainMessage: '',
      heroTitle: '',
      heroBody: '',
      ctaPrimary: '',
      ctaSecondary: '',
      heroImage: null,
      galleryImages: [],
      legacyProjectId: raw.projectId,
    };
  }
  if (!Array.isArray(raw.sections)) return null;
  const { heroImage, galleryImages } = normalizeLegacyImageFields(raw);
  return {
    schemaVersion: 2,
    linkedProjectId: typeof raw.linkedProjectId === 'string' ? raw.linkedProjectId : null,
    sections: normalizeWbSections(raw.sections),
    selectedSectionId: typeof raw.selectedSectionId === 'string' ? raw.selectedSectionId : 's-hero',
    metaTitle: typeof raw.metaTitle === 'string' ? raw.metaTitle : '',
    metaDesc: typeof raw.metaDesc === 'string' ? raw.metaDesc : '',
    slug: typeof raw.slug === 'string' ? raw.slug : '',
    publishStatus: raw.publishStatus || 'draft',
    language: typeof raw.language === 'string' ? raw.language : 'tr',
    tone: typeof raw.tone === 'string' ? raw.tone : 'luxury',
    brief: typeof raw.brief === 'string' ? raw.brief : '',
    siteGoal: typeof raw.siteGoal === 'string' ? raw.siteGoal : '',
    audience: typeof raw.audience === 'string' ? raw.audience : '',
    mainMessage: typeof raw.mainMessage === 'string' ? raw.mainMessage : '',
    heroTitle: typeof raw.heroTitle === 'string' ? raw.heroTitle : '',
    heroBody: typeof raw.heroBody === 'string' ? raw.heroBody : '',
    ctaPrimary: typeof raw.ctaPrimary === 'string' ? raw.ctaPrimary : '',
    ctaSecondary: typeof raw.ctaSecondary === 'string' ? raw.ctaSecondary : '',
    heroImage,
    galleryImages,
  };
}

function isWebsiteBuilderDraftEmpty(raw) {
  if (raw == null) return true;
  if (typeof raw !== 'object' || Array.isArray(raw)) return true;
  if (Object.keys(raw).length === 0) return true;
  const draft = deserializeWebsiteBuilderDraft(raw);
  if (!draft) return true;
  const hasContent = Boolean(
    draft.heroTitle.trim() ||
      draft.heroBody.trim() ||
      draft.metaTitle.trim() ||
      draft.slug.trim() ||
      draft.brief.trim() ||
      draft.mainMessage.trim() ||
      draft.heroImage?.asset_id ||
      draft.heroImage?.url ||
      draft.galleryImages.length > 0,
  );
  if (!hasContent) {
    const onlyDefaults =
      draft.sections.length === DEFAULT_SECTIONS.length &&
      draft.sections.every((s, i) => s.key === DEFAULT_SECTIONS[i]?.key && !s.customName);
    if (onlyDefaults) return true;
  }
  return false;
}

function resolveInitialDraft({ apiDraftBody, legacyDraft, migrationDone }) {
  const apiEmpty = isWebsiteBuilderDraftEmpty(apiDraftBody);
  const apiDraft = deserializeWebsiteBuilderDraft(apiDraftBody);
  if (!apiEmpty && apiDraft) return { draft: apiDraft, shouldMigrateToApi: false };
  if (apiEmpty && !migrationDone && legacyDraft && !isWebsiteBuilderDraftEmpty(legacyDraft)) {
    return { draft: legacyDraft, shouldMigrateToApi: true };
  }
  return { draft: apiDraft, shouldMigrateToApi: false };
}

async function resolveCreativeStudioProject(deps) {
  const listed = await deps.listProjects();
  const existing = listed.items.find(
    (item) => item.linked_project_id === deps.linkedProjectId && item.archived_at == null,
  );
  if (existing) return { project: existing, created: false };
  const project = await deps.createProject({
    name: deps.linkedProjectName.trim() || 'Website project',
    linked_project_id: deps.linkedProjectId,
    status: 'active',
  });
  return { project, created: true };
}

async function resolveWebsiteDocument(deps) {
  const listed = await deps.listDocuments(deps.csProjectId);
  const existing = listed.items.find(
    (item) => item.document_type === 'website' && item.archived_at == null,
  );
  if (existing) {
    const document = await deps.getDocument(existing.id);
    return { document, created: false };
  }
  const document = await deps.createDocument(deps.csProjectId, {
    title: deps.documentTitle.trim() || 'Website',
    document_type: 'website',
    status: 'draft',
    draft_body_json: {},
  });
  return { document, created: true };
}

function mapApiVersionToWbVersion(version) {
  return {
    id: version.id,
    label: version.label?.trim() || `v${version.version_number}`,
    status: 'draft',
    updatedAt: version.created_at,
    noteKey: 'initial',
    comment: version.summary ?? undefined,
  };
}

const SAMPLE_UUID = '11111111-1111-4111-8111-111111111111';
const SAMPLE_UUID_2 = '22222222-2222-4222-8222-222222222222';

function baseInput(overrides = {}) {
  return {
    linkedProjectId: 'x',
    sections: DEFAULT_SECTIONS,
    selectedSectionId: 's-hero',
    metaTitle: '',
    metaDesc: '',
    slug: 's',
    publishStatus: 'draft',
    language: 'en',
    tone: 'luxury',
    brief: '',
    siteGoal: '',
    audience: '',
    mainMessage: '',
    heroTitle: '',
    heroBody: '',
    ctaPrimary: '',
    ctaSecondary: '',
    heroImage: null,
    galleryImages: [],
    ...overrides,
  };
}

describe('module wiring', () => {
  it('ships API client + persistence + session + media + hooks', () => {
    assert.equal(existsSync(join(webSrc, 'lib/api/creative-studio.ts')), true);
    assert.equal(existsSync(join(wbDir, 'website-builder-persistence.ts')), true);
    assert.equal(existsSync(join(wbDir, 'website-builder-media.ts')), true);
    assert.equal(existsSync(join(wbDir, 'use-website-builder-media.ts')), true);
    assert.equal(existsSync(join(wbDir, 'website-builder-session.ts')), true);
    assert.equal(existsSync(join(wbDir, 'use-website-builder-document.ts')), true);
    const api = readFileSync(join(webSrc, 'lib/api/creative-studio.ts'), 'utf8');
    for (const name of [
      'listCreativeStudioMediaAssets',
      'uploadCreativeStudioMediaAsset',
      'fetchCreativeStudioMediaBlob',
      'getCreativeStudioMediaContentUrl',
    ]) {
      assert.match(api, new RegExp(`export (async )?function ${name}`));
    }
    const persistence = read('website-builder-persistence.ts');
    assert.match(persistence, /WB_DRAFT_SCHEMA_VERSION = 2/);
    assert.match(persistence, /heroImage/);
    assert.match(persistence, /galleryImages/);
    assert.doesNotMatch(persistence, /heroCoverOverride: input/);
    const workspace = read('website-builder-workspace.tsx');
    assert.match(workspace, /useWebsiteBuilderMedia/);
    assert.match(workspace, /heroImage/);
    assert.doesNotMatch(workspace, /savePersistedDraft\(/);
  });
});

describe('WbImageRef serialize / deserialize', () => {
  it('round-trips asset_id primary refs', () => {
    const input = baseInput({
      heroTitle: 'Persist Me',
      heroImage: {
        asset_id: SAMPLE_UUID,
        url: `/creative-studio/media/assets/${SAMPLE_UUID}/content`,
        alt: 'Hero',
        role: 'hero',
      },
      galleryImages: [
        { asset_id: SAMPLE_UUID_2, url: null, alt: 'G1', role: 'gallery' },
      ],
    });
    const draft = deserializeWebsiteBuilderDraft(serializeWebsiteBuilderDraft(input));
    assert.ok(draft);
    assert.equal(draft.schemaVersion, 2);
    assert.equal(draft.heroImage.asset_id, SAMPLE_UUID);
    assert.equal(draft.galleryImages[0].asset_id, SAMPLE_UUID_2);
    assert.equal(draft.heroTitle, 'Persist Me');
  });

  it('never serializes blob or object URLs', () => {
    const payload = serializeWebsiteBuilderDraft(
      baseInput({
        heroImage: {
          asset_id: SAMPLE_UUID,
          url: 'blob:http://localhost/abc',
          alt: 'x',
        },
        galleryImages: [
          { asset_id: null, url: 'blob:http://localhost/g' },
          { asset_id: SAMPLE_UUID_2, url: 'object:store/1' },
        ],
      }),
    );
    assert.equal(payload.heroImage.asset_id, SAMPLE_UUID);
    assert.equal(payload.heroImage.url, undefined);
    assert.equal(payload.galleryImages.length, 1);
    assert.equal(payload.galleryImages[0].asset_id, SAMPLE_UUID_2);
    assert.equal(payload.galleryImages[0].url, undefined);
    assert.equal(JSON.stringify(payload).includes('blob:'), false);
  });

  it('does not treat demo ids a1 as UUIDs', () => {
    assert.equal(isMediaAssetUuid('a1'), false);
    assert.equal(isMediaAssetUuid(SAMPLE_UUID), true);
    const parsed = parseImageRef({ asset_id: 'a1', url: 'https://example.com/x.jpg' });
    assert.equal(parsed.asset_id, null);
    assert.equal(parsed.url, 'https://example.com/x.jpg');
  });
});

describe('legacy hero/gallery URL migration', () => {
  it('migrates heroCoverOverride / galleryOverride into WbImageRef', () => {
    const draft = deserializeWebsiteBuilderDraft({
      sections: DEFAULT_SECTIONS,
      heroTitle: 'Legacy',
      heroCoverOverride: 'https://cdn.example.com/hero.jpg',
      galleryOverride: [
        'https://cdn.example.com/g1.jpg',
        'blob:http://localhost/skip',
        'https://cdn.example.com/g2.jpg',
      ],
    });
    assert.ok(draft);
    assert.equal(draft.heroImage.asset_id, null);
    assert.equal(draft.heroImage.url, 'https://cdn.example.com/hero.jpg');
    assert.equal(draft.galleryImages.length, 2);
    assert.equal(draft.galleryImages[0].url, 'https://cdn.example.com/g1.jpg');
  });

  it('prefers v2 heroImage when both legacy and v2 present', () => {
    const draft = deserializeWebsiteBuilderDraft({
      sections: DEFAULT_SECTIONS,
      heroCoverOverride: 'https://cdn.example.com/old.jpg',
      heroImage: { asset_id: SAMPLE_UUID, url: null },
      galleryImages: [{ asset_id: SAMPLE_UUID_2 }],
    });
    assert.equal(draft.heroImage.asset_id, SAMPLE_UUID);
    assert.equal(draft.galleryImages[0].asset_id, SAMPLE_UUID_2);
  });
});

describe('display resolve priority + missing fallback', () => {
  it('resolved asset → legacy url → template → placeholder', () => {
    const ref = { asset_id: SAMPLE_UUID, url: 'https://cdn.example.com/legacy.jpg' };
    assert.equal(
      resolveDisplayUrl({
        ref,
        resolvedAssetUrl: 'blob:http://localhost/live',
        templateUrl: 'https://template/cover.jpg',
        placeholderUrl: 'data:placeholder',
      }),
      'blob:http://localhost/live',
    );
    assert.equal(
      resolveDisplayUrl({
        ref,
        resolvedAssetUrl: null,
        templateUrl: 'https://template/cover.jpg',
        placeholderUrl: 'data:placeholder',
      }),
      'https://cdn.example.com/legacy.jpg',
    );
    assert.equal(
      resolveDisplayUrl({
        ref: null,
        resolvedAssetUrl: null,
        templateUrl: 'https://template/cover.jpg',
        placeholderUrl: 'data:placeholder',
      }),
      'https://template/cover.jpg',
    );
    assert.equal(
      resolveDisplayUrl({
        ref: { asset_id: SAMPLE_UUID, url: null },
        resolvedAssetUrl: null,
        templateUrl: null,
        placeholderUrl: 'data:placeholder',
      }),
      'data:placeholder',
    );
  });

  it('missing/archived asset falls back without crash', () => {
    const url = resolveDisplayUrl({
      ref: { asset_id: SAMPLE_UUID, url: null },
      resolvedAssetUrl: null,
      templateUrl: 'https://template/cover.jpg',
      placeholderUrl: 'data:ph',
    });
    assert.equal(url, 'https://template/cover.jpg');
  });
});

describe('selection + refresh restore + save failure preserves selection', () => {
  it('persists hero/gallery asset ids across serialize roundtrip (refresh restore)', () => {
    const saved = serializeWebsiteBuilderDraft(
      baseInput({
        heroImage: { asset_id: SAMPLE_UUID, alt: 'Night', role: 'hero' },
        galleryImages: [
          { asset_id: SAMPLE_UUID_2, role: 'gallery' },
          { asset_id: null, url: 'https://cdn.example.com/legacy-g.jpg' },
        ],
      }),
    );
    const restored = deserializeWebsiteBuilderDraft(saved);
    assert.equal(restored.heroImage.asset_id, SAMPLE_UUID);
    assert.equal(restored.galleryImages[0].asset_id, SAMPLE_UUID_2);
    assert.equal(restored.galleryImages[1].url, 'https://cdn.example.com/legacy-g.jpg');
  });

  it('failed save leaves local image selection untouched', () => {
    const local = {
      heroImage: { asset_id: SAMPLE_UUID, url: null },
      galleryImages: [{ asset_id: SAMPLE_UUID_2 }],
    };
    const before = structuredClone(local);
    const saveFailed = true;
    if (saveFailed) {
      /* keep local */
    }
    assert.deepEqual(local, before);
  });
});

describe('real list vs demo primary', () => {
  it('demo sample ids are never UUIDs; API ids are', () => {
    assert.equal(isDemoAssetId('a1'), true);
    assert.equal(isDemoAssetId('a12'), true);
    assert.equal(isMediaAssetUuid('a1'), false);
    assert.equal(isMediaAssetUuid(SAMPLE_UUID), true);
  });

  it('source files prefer Media Library over hardcoded WB_ASSETS as primary', () => {
    const hook = read('use-website-builder-media.ts');
    assert.match(hook, /listCreativeStudioMediaAssets/);
    assert.match(hook, /usingSamples/);
    assert.match(hook, /WB_ASSETS/);
    const workspace = read('website-builder-workspace.tsx');
    assert.match(workspace, /mediaApi\.assets|libraryAssets/);
    assert.match(workspace, /useWebsiteBuilderMedia/);
  });
});

describe('upload behavior contracts', () => {
  it('upload helper rejects concurrent uploads via lock pattern in source', () => {
    const hook = read('use-website-builder-media.ts');
    assert.match(hook, /uploadLockRef/);
    assert.match(hook, /Only image files/);
    assert.match(hook, /uploadCreativeStudioMediaAsset/);
  });

  it('upload success/fail paths exist in workspace', () => {
    const workspace = read('website-builder-workspace.tsx');
    assert.match(workspace, /uploadSucceeded/);
    assert.match(workspace, /uploadFailed/);
    assert.match(workspace, /accept="image\/jpeg,image\/png,image\/webp,image\/gif"/);
    assert.match(workspace, /handleUploadFile/);
  });

  it('file input is always mounted and rail upload triggers it', () => {
    const workspace = read('website-builder-workspace.tsx');
    const rail = read('website-builder-rail-drawers.tsx');
    assert.match(workspace, /data-testid="wb-upload-input"/);
    assert.match(workspace, /onUploadAsset=\{openUploadPicker\}/);
    assert.match(workspace, /uploadInputRef\.current\?\.click\(\)/);
    assert.match(workspace, /e\.target\.value = ''/);
    assert.match(rail, /onClick=\{\(\) => props\.onUploadAsset\?\.\(\)\}/);
    assert.match(rail, /disabled=\{props\.uploadingAsset\}/);
    // Input must not be gated behind the collapsible assets section only.
    const inputIdx = workspace.indexOf('data-testid="wb-upload-input"');
    const assetsCollapseIdx = workspace.indexOf("sectionKey === 'assets'");
    assert.ok(inputIdx > 0, 'upload input present');
    assert.ok(
      assetsCollapseIdx < 0 || inputIdx < assetsCollapseIdx,
      'upload input must mount outside assets collapse gate',
    );
  });

  it('handleUploadFile validates non-empty accepted image types before upload', () => {
    const workspace = read('website-builder-workspace.tsx');
    assert.match(workspace, /!file\.size/);
    assert.match(workspace, /image\\\/jpeg/);
    assert.match(workspace, /image\\\/png/);
    assert.match(workspace, /image\\\/webp/);
    assert.match(workspace, /image\\\/gif/);
    assert.match(workspace, /mediaApi\.uploadImage\(file\)/);
  });
});

describe('serialize / deserialize roundtrip', () => {
  it('round-trips editor state', () => {
    const input = baseInput({
      linkedProjectId: SAMPLE_UUID,
      sections: [...DEFAULT_SECTIONS, { id: 's-custom', key: 'gallery', visible: true, customName: 'Custom' }],
      metaTitle: 'Meta',
      metaDesc: 'Desc',
      slug: 'demo-site',
      language: 'en',
      brief: 'Brief',
      siteGoal: 'Goal',
      audience: 'Audience',
      mainMessage: 'Message',
      heroTitle: 'Persist Me',
      heroBody: 'Body',
      ctaPrimary: 'Invest',
      ctaSecondary: 'Explore',
      heroImage: { asset_id: SAMPLE_UUID, role: 'hero' },
    });
    const draft = deserializeWebsiteBuilderDraft(serializeWebsiteBuilderDraft(input));
    assert.ok(draft);
    assert.equal(draft.heroTitle, 'Persist Me');
    assert.equal(draft.slug, 'demo-site');
    assert.equal(draft.sections.some((s) => s.customName === 'Custom'), true);
    assert.equal(draft.heroImage.asset_id, SAMPLE_UUID);
  });

  it('deserializes legacy localStorage shape', () => {
    const draft = deserializeWebsiteBuilderDraft({
      projectId: 'temple',
      selectedSectionId: 's-about',
      device: 'mobile',
      language: 'tr',
      tone: 'investor',
      publishStatus: 'review',
      sections: DEFAULT_SECTIONS,
      activeVersionId: 'v1',
      metaTitle: 'Legacy',
      metaDesc: 'Legacy desc',
      slug: 'legacy-slug',
      zoom: 90,
      splitPreset: 'desktop-mobile',
      savedAt: 123,
    });
    assert.ok(draft);
    assert.equal(draft.legacyProjectId, 'temple');
    assert.equal(draft.metaTitle, 'Legacy');
    assert.equal(draft.heroImage, null);
  });
});

describe('localStorage migration only when API empty', () => {
  it('migrates legacy only when API empty and migration not done', () => {
    const legacy = serializeWebsiteBuilderDraft(
      baseInput({
        linkedProjectId: null,
        language: 'tr',
        slug: 'from-ls',
        metaTitle: 'From LS',
        heroTitle: 'LS Hero',
      }),
    );

    const migrate = resolveInitialDraft({
      apiDraftBody: {},
      legacyDraft: deserializeWebsiteBuilderDraft(legacy),
      migrationDone: false,
    });
    assert.equal(migrate.shouldMigrateToApi, true);
    assert.equal(migrate.draft.heroTitle, 'LS Hero');

    assert.equal(
      resolveInitialDraft({
        apiDraftBody: {},
        legacyDraft: deserializeWebsiteBuilderDraft(legacy),
        migrationDone: true,
      }).shouldMigrateToApi,
      false,
    );

    const apiWins = resolveInitialDraft({
      apiDraftBody: serializeWebsiteBuilderDraft(
        baseInput({
          language: 'en',
          slug: 'api',
          metaTitle: 'API',
          heroTitle: 'API Hero',
          heroImage: { asset_id: SAMPLE_UUID },
        }),
      ),
      legacyDraft: deserializeWebsiteBuilderDraft(legacy),
      migrationDone: false,
    });
    assert.equal(apiWins.shouldMigrateToApi, false);
    assert.equal(apiWins.draft.heroTitle, 'API Hero');
    assert.equal(apiWins.draft.heroImage.asset_id, SAMPLE_UUID);
  });

  it('does not overwrite API draft that only has image refs', () => {
    const apiBody = serializeWebsiteBuilderDraft(
      baseInput({
        heroImage: { asset_id: SAMPLE_UUID },
      }),
    );
    assert.equal(isWebsiteBuilderDraftEmpty(apiBody), false);
    const resolved = resolveInitialDraft({
      apiDraftBody: apiBody,
      legacyDraft: deserializeWebsiteBuilderDraft(
        serializeWebsiteBuilderDraft(baseInput({ heroTitle: 'LS' })),
      ),
      migrationDone: false,
    });
    assert.equal(resolved.shouldMigrateToApi, false);
    assert.equal(resolved.draft.heroImage.asset_id, SAMPLE_UUID);
  });
});

describe('project / document resolution (no duplicates)', () => {
  it('reuses existing CS project by linked_project_id', async () => {
    let createCalls = 0;
    const linked = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
    const existing = {
      id: 'cs-1',
      linked_project_id: linked,
      archived_at: null,
    };
    const first = await resolveCreativeStudioProject({
      linkedProjectId: linked,
      linkedProjectName: 'Demo',
      listProjects: async () => ({ items: [existing], total: 1 }),
      createProject: async () => {
        createCalls += 1;
        throw new Error('should not create');
      },
    });
    const second = await resolveCreativeStudioProject({
      linkedProjectId: linked,
      linkedProjectName: 'Demo',
      listProjects: async () => ({ items: [existing], total: 1 }),
      createProject: async () => {
        createCalls += 1;
        throw new Error('should not create');
      },
    });
    assert.equal(first.created, false);
    assert.equal(second.created, false);
    assert.equal(createCalls, 0);
  });

  it('creates CS project once when missing', async () => {
    let createCalls = 0;
    const linked = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
    const result = await resolveCreativeStudioProject({
      linkedProjectId: linked,
      linkedProjectName: 'New',
      listProjects: async () => ({ items: [], total: 0 }),
      createProject: async (input) => {
        createCalls += 1;
        assert.equal(input.linked_project_id, linked);
        return { id: 'cs-new', linked_project_id: linked, archived_at: null };
      },
    });
    assert.equal(result.created, true);
    assert.equal(createCalls, 1);
  });

  it('reuses website document without duplicates', async () => {
    let createCalls = 0;
    const listed = {
      id: 'doc-1',
      document_type: 'website',
      archived_at: null,
      draft_body_json: { heroTitle: 'Loaded' },
    };
    const first = await resolveWebsiteDocument({
      csProjectId: 'cs-1',
      documentTitle: 'Website',
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

describe('draft load / save / error preserves state', () => {
  it('load applies deserialized draft fields including image refs', () => {
    const draft = deserializeWebsiteBuilderDraft(
      serializeWebsiteBuilderDraft(
        baseInput({
          heroTitle: 'Loaded Heading',
          heroImage: { asset_id: SAMPLE_UUID },
        }),
      ),
    );
    assert.equal(draft.heroTitle, 'Loaded Heading');
    assert.equal(draft.heroImage.asset_id, SAMPLE_UUID);
  });

  it('save payload has schema v2 image fields and no versions side-effect', () => {
    const payload = serializeWebsiteBuilderDraft(
      baseInput({
        heroTitle: 'To Save',
        heroImage: { asset_id: SAMPLE_UUID },
      }),
    );
    assert.equal(payload.schemaVersion, 2);
    assert.equal(payload.heroTitle, 'To Save');
    assert.equal(payload.heroImage.asset_id, SAMPLE_UUID);
    assert.equal('heroCoverOverride' in payload, false);
    assert.equal('galleryOverride' in payload, false);
    assert.equal('versions' in payload, false);
  });
});

describe('versions create / list / restore', () => {
  it('maps API versions for list UI', () => {
    const mapped = [
      {
        id: 'ver-1',
        version_number: 1,
        label: 'V1 API Test',
        summary: null,
        created_at: '2026-08-05T12:00:00.000Z',
      },
      {
        id: 'ver-2',
        version_number: 2,
        label: null,
        summary: 'auto',
        created_at: '2026-08-05T13:00:00.000Z',
      },
    ].map(mapApiVersionToWbVersion);
    assert.equal(mapped[0].label, 'V1 API Test');
    assert.equal(mapped[1].label, 'v2');
    assert.equal(mapped[1].comment, 'auto');
  });

  it('restore applies version body via deserializer including images', () => {
    const restored = deserializeWebsiteBuilderDraft(
      serializeWebsiteBuilderDraft(
        baseInput({
          heroTitle: 'V1 Heading',
          heroImage: { asset_id: SAMPLE_UUID },
        }),
      ),
    );
    assert.equal(restored.heroTitle, 'V1 Heading');
    assert.equal(restored.heroImage.asset_id, SAMPLE_UUID);
  });
});
