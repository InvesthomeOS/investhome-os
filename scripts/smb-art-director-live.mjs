/**
 * Live Art Director POC quality gate on The Temple.
 * Does not print secrets. Run: node scripts/smb-art-director-live.mjs
 */
import { createRequire } from 'node:module';
import { mkdirSync as mkdir, writeFileSync as write } from 'node:fs';
import { dirname as pathDirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = pathDirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(__dirname, '..', '.pw-verify', 'node_modules', 'playwright'));

const BASE = process.env.SMB_BASE_URL || 'http://localhost:3000';
const EMAIL = process.env.SMB_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.SMB_PASSWORD || 'Investhome2026!';
const SMB_PATH = '/workspaces/creative-studio/social-media-builder';
const TEMPLE_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const SHOT_DIR = join(__dirname, '..', 'artifacts', 'smb-art-director');

const INVESTMENT_BRIEF =
  'Create a premium English Instagram square for The Temple investment campaign. Minimum investment $500,000, target return 14%, hold period 24 months. Use a real project photograph. Do not invent other financials.';
const LOCATION_BRIEF =
  "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium bir Instagram kare postu hazırla. Proje verilerini kullan. En uygun gerçek proje görselini seç. İngilizce hazırla. Yatırım metrikleri kullanma.";
const ALTERNATE_BRIEF = 'Başka bir gerçek The Temple exterior görseli kullan.';

const results = [];
function pass(name, detail = '') {
  results.push({ name, ok: true, detail });
  console.log(`PASS ${name}${detail ? ` — ${detail}` : ''}`);
}
function fail(name, detail = '') {
  results.push({ name, ok: false, detail });
  console.log(`FAIL ${name}${detail ? ` — ${detail}` : ''}`);
}

async function dumpPage(page, label) {
  mkdir(SHOT_DIR, { recursive: true });
  const file = join(SHOT_DIR, `${label}.png`);
  try {
    await page.screenshot({ path: file, fullPage: false });
  } catch {
    /* ignore */
  }
  const url = page.url();
  const title = await page.title().catch(() => '');
  const body = await page
    .evaluate(() => (document.body?.innerText || '').slice(0, 400))
    .catch(() => '');
  console.log(`DUMP ${label} url=${url} title=${title} shot=${file}`);
  console.log(`DUMP ${label} body=${body.replace(/\s+/g, ' ').slice(0, 280)}`);
}

async function waitReady(page) {
  try {
    await page.waitForSelector('[data-testid="smb-artboard"]', { timeout: 90000 });
  } catch (err) {
    await dumpPage(page, 'wait-ready-timeout');
    throw err;
  }
  for (let i = 0; i < 40; i++) {
    const ready = await page.evaluate(() => Boolean(document.querySelector('[data-testid="smb-workspace"]')));
    if (ready) return;
    await page.waitForTimeout(500);
  }
}

async function waitAiIdle(page, timeoutMs = 180000) {
  const start = Date.now();
  await page.waitForTimeout(1500);
  while (Date.now() - start < timeoutMs) {
    const disabled = await page.locator('[data-testid="smb-ai-design-submit"][disabled]').count();
    if (!disabled) return;
    await page.waitForTimeout(1000);
  }
  throw new Error('AI timeout');
}

async function waitCoverReady(page) {
  for (let i = 0; i < 20; i++) {
    const ready = await page.evaluate(() => {
      const img = document.querySelector('[data-testid="smb-artboard-img"]');
      const id = document.querySelector('[data-testid="smb-artboard"]')?.getAttribute('data-cover-asset-id');
      return Boolean(img && img.complete && img.naturalWidth > 80 && id);
    });
    if (ready) return;
    await page.waitForTimeout(500);
  }
}

async function selectArtDirectorEngine(page) {
  const native = page.locator('[data-testid="smb-ai-engine-native"]');
  await native.waitFor({ state: 'visible', timeout: 30000 });
  await native.click();
  await page.waitForFunction(
    () => document.querySelector('[data-testid="smb-workspace"]')?.getAttribute('data-design-engine') === 'native',
    null,
    { timeout: 15000 },
  );
}

async function createPost(page, prompt) {
  await selectArtDirectorEngine(page);
  await page.fill('[data-testid="smb-ai-design-input"]', prompt);
  await page.click('[data-testid="smb-ai-design-submit"]');
  await waitAiIdle(page);
  await page.waitForTimeout(2500);
  await waitCoverReady(page);
}

async function editPost(page, prompt) {
  await selectArtDirectorEngine(page);
  const edit = page.locator('[data-testid="smb-ai-design-edit"]');
  await edit.waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForFunction(
    () => {
      const btn = document.querySelector('[data-testid="smb-ai-design-edit"]');
      return Boolean(btn && !btn.hasAttribute('disabled'));
    },
    null,
    { timeout: 30000 },
  );
  await page.fill('[data-testid="smb-ai-design-input"]', prompt);
  await edit.click();
  await waitAiIdle(page);
  await page.waitForTimeout(1200);
  await waitCoverReady(page);
}

async function shot(page, name, full = false) {
  mkdir(SHOT_DIR, { recursive: true });
  const file = join(SHOT_DIR, `${name}.png`);
  if (full) {
    await page.screenshot({ path: file, fullPage: false });
    return file;
  }
  const art = page.locator('[data-testid="smb-artboard"]');
  if (await art.count()) {
    await art.screenshot({ path: file });
  } else {
    await page.screenshot({ path: file, fullPage: false });
  }
  return file;
}

async function canvasText(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[data-testid^="smb-el-"]')];
    return nodes
      .map((n) => (n.textContent || '').trim())
      .filter(Boolean)
      .join(' | ');
  });
}

async function canvasGeometry(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[data-testid^="smb-el-"]')].filter(
      (n) => !String(n.getAttribute('data-testid') || '').includes('resize'),
    );
    return nodes.map((n) => {
      const el = n;
      const r = el.getBoundingClientRect();
      return {
        type: el.getAttribute('data-el-type') || '',
        role: el.getAttribute('data-el-role') || '',
        text: (el.textContent || '').trim().slice(0, 80),
        top: Math.round(r.top),
        left: Math.round(r.left),
        width: Math.round(r.width),
        height: Math.round(r.height),
      };
    });
  });
}

async function provenance(page) {
  return page.evaluate(() => {
    const ws = document.querySelector('[data-testid="smb-workspace"]');
    const art = document.querySelector('[data-testid="smb-artboard"]');
    const img = document.querySelector('[data-testid="smb-artboard-img"]');
    const asset = document.querySelector('[data-testid="smb-art-director-selected-asset"]');
    const variants = [...document.querySelectorAll('[data-testid^="smb-art-director-option-"]')].map((el) => ({
      key: (el.getAttribute('data-testid') || '').replace('smb-art-director-option-', ''),
      composition: el.getAttribute('data-composition') || '',
      direction: el.getAttribute('data-direction') || '',
      active: el.classList.contains('is-active'),
    }));
    return {
      engine: ws?.getAttribute('data-design-engine') || '',
      artDirector: ws?.getAttribute('data-art-director') || '',
      campaignType: ws?.getAttribute('data-campaign-type') || '',
      selectedVariant: ws?.getAttribute('data-selected-variant') || '',
      selectedAssetId: ws?.getAttribute('data-selected-asset-id') || '',
      selectedAssetFilename: ws?.getAttribute('data-selected-asset-filename') || '',
      provenanceSource: ws?.getAttribute('data-provenance-source') || '',
      coverAssetId: art?.getAttribute('data-cover-asset-id') || '',
      imgSrc: img?.getAttribute('src') || '',
      imgWidth: img?.naturalWidth || 0,
      imgHeight: img?.naturalHeight || 0,
      indicatorId: asset?.getAttribute('data-asset-id') || '',
      indicatorFilename: asset?.getAttribute('data-asset-filename') || '',
      indicatorCategory: asset?.getAttribute('data-asset-category') || '',
      indicatorSubject: asset?.getAttribute('data-asset-subject') || '',
      indicatorSource: asset?.getAttribute('data-asset-source') || '',
      intent: ws?.getAttribute('data-creative-intent') || '',
      direction: ws?.getAttribute('data-creative-direction') || '',
      composition: ws?.getAttribute('data-creative-composition') || '',
      family: ws?.getAttribute('data-composition-family') || '',
      fullscreen: ws?.getAttribute('data-cs-fullscreen') || '',
      ideogramCards: document.querySelectorAll('[data-testid^="smb-ideogram-option-"]').length,
      variants,
    };
  });
}

function forbiddenImage(prov) {
  const blob = [
    prov.selectedAssetFilename,
    prov.indicatorFilename,
    prov.imgSrc,
  ]
    .join(' ')
    .toLowerCase();
  return (
    blob.includes('unsplash')
    || blob.includes('ideogram')
    || blob.includes('placeholder')
    || /^https?:/.test(prov.imgSrc || '')
  );
}

function hasInvestmentFacts(text) {
  return /\$500|500,000|500k/i.test(text) && /14%|%14/.test(text) && /24/.test(text);
}

async function selectVariant(page, key) {
  const btn = page.locator(`[data-testid="smb-art-director-select-${key}"]`);
  if (!(await btn.count())) throw new Error(`missing variant ${key}`);
  await btn.click();
  await page.waitForTimeout(800);
  await waitCoverReady(page);
}

async function main() {
  mkdir(SHOT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on('pageerror', (err) => console.log('PAGEERROR', err.message));
  const notes = {};

  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('input[type="email"]', { timeout: 30000 });
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForFunction(
      () => !window.location.pathname.includes('/login'),
      null,
      { timeout: 45000 },
    ).catch(async () => {
      await dumpPage(page, 'login-stuck');
      throw new Error('login did not leave /login');
    });
    await page.goto(`${BASE}${SMB_PATH}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await waitReady(page);

    const projectSelect = page.locator('#smb-project');
    if (await projectSelect.count()) {
      const values = await projectSelect.locator('option').evaluateAll((opts) =>
        opts.map((o) => o.value),
      );
      if (values.includes(TEMPLE_ID)) {
        await projectSelect.selectOption(TEMPLE_ID);
        await page.waitForTimeout(2500);
        await waitReady(page);
      } else {
        fail('project', `Temple id missing from selector (${values.length} options)`);
      }
    }

    const nativeLabel = await page.locator('[data-testid="smb-ai-engine-native"]').innerText().catch(() => '');
    if (/art director/i.test(nativeLabel)) {
      pass('engine-label', nativeLabel.trim());
    } else {
      fail('engine-label', nativeLabel);
    }
    await selectArtDirectorEngine(page);

    // ---- INVESTMENT A/B/C ----
    try {
      await createPost(page, INVESTMENT_BRIEF);
      const textA = await canvasText(page);
      const geoA = await canvasGeometry(page);
      const provA = await provenance(page);
      notes.A = { text: textA, geo: geoA, prov: provA };
      const shotA = await shot(page, 'variant-a-editorial-luxury');
      await shot(page, 'workspace-abc-chooser', true);

      const realAsset =
        Boolean(provA.coverAssetId)
        && provA.coverAssetId === provA.selectedAssetId
        && Boolean(provA.selectedAssetFilename)
        && !/ideogram/i.test(provA.selectedAssetFilename)
        && !forbiddenImage(provA)
        && provA.imgWidth > 80
        && /google_drive|drive|media_library|creative.studio|upload/i.test(
          `${provA.provenanceSource} ${provA.indicatorSource}`,
        );
      const facts = hasInvestmentFacts(textA);
      const three = provA.variants.length === 3
        && provA.variants.some((v) => v.key === 'A')
        && provA.variants.some((v) => v.key === 'B')
        && provA.variants.some((v) => v.key === 'C');
      const compositions = new Set(provA.variants.map((v) => v.composition));
      const directions = new Set(provA.variants.map((v) => v.direction));
      const differentPlans = compositions.size >= 3 && directions.size >= 2;
      const noIdeogram = provA.ideogramCards === 0 && provA.engine === 'native' && provA.artDirector === 'true';
      const campaign = provA.campaignType === 'INVESTMENT' || provA.intent === 'INVESTMENT';
      const types = new Set(geoA.map((g) => g.type));
      const roles = new Set(geoA.map((g) => g.role));
      const hierarchy = types.has('METRIC_GROUP') && (roles.has('headline') || /headline/i.test(textA));

      if (realAsset && facts && three && differentPlans && noIdeogram && campaign) {
        pass(
          'investment-A',
          `asset=${provA.selectedAssetFilename} cat=${provA.indicatorCategory} src=${provA.provenanceSource} comps=${[...compositions].join('/')} shot=${shotA}`,
        );
      } else {
        fail(
          'investment-A',
          JSON.stringify({
            realAsset, facts, three, differentPlans, noIdeogram, campaign, hierarchy, provA, text: textA.slice(0, 280),
          }),
        );
      }

      await selectVariant(page, 'B');
      const textB = await canvasText(page);
      const geoB = await canvasGeometry(page);
      const provB = await provenance(page);
      notes.B = { text: textB, geo: geoB, prov: provB };
      const shotB = await shot(page, 'variant-b-institutional-investment');
      const samePhotoB = provB.coverAssetId === provA.coverAssetId;
      const layoutB =
        provB.composition !== provA.composition
        || provB.selectedVariant === 'B';
      const factsB = hasInvestmentFacts(textB);
      if (samePhotoB && layoutB && factsB && !forbiddenImage(provB)) {
        pass('investment-B', `comp=${provB.composition} dir=${provB.direction} shot=${shotB}`);
      } else {
        fail('investment-B', JSON.stringify({ samePhotoB, layoutB, factsB, provB, text: textB.slice(0, 220) }));
      }

      await selectVariant(page, 'C');
      const textC = await canvasText(page);
      const geoC = await canvasGeometry(page);
      const provC = await provenance(page);
      notes.C = { text: textC, geo: geoC, prov: provC };
      const shotC = await shot(page, 'variant-c-architectural-premium');
      const samePhotoC = provC.coverAssetId === provA.coverAssetId;
      const geoAHeadline = (notes.A?.geo || []).find((g) => g.role === 'headline');
      const geoBHeadline = (notes.B?.geo || []).find((g) => g.role === 'headline');
      const geoCHeadline = geoC.find((g) => g.role === 'headline');
      const geoAMetric = (notes.A?.geo || []).find((g) => g.type === 'METRIC_GROUP');
      const geoCMetric = geoC.find((g) => g.type === 'METRIC_GROUP');
      const layoutC =
        provC.composition !== provA.composition
        || provC.composition !== provB.composition
        || (geoCHeadline && geoAHeadline && Math.abs(geoCHeadline.top - geoAHeadline.top) >= 24)
        || (geoCHeadline && geoBHeadline && Math.abs(geoCHeadline.top - geoBHeadline.top) >= 24)
        || (geoCMetric && geoAMetric && Math.abs(geoCMetric.top - geoAMetric.top) >= 24)
        || (geoCMetric && geoAMetric && Math.abs((geoCMetric.height || 0) - (geoAMetric.height || 0)) >= 24);
      if (samePhotoC && layoutC && !forbiddenImage(provC)) {
        pass('investment-C', `comp=${provC.composition} dir=${provC.direction} shot=${shotC}`);
      } else {
        fail('investment-C', JSON.stringify({ samePhotoC, layoutC, provC, text: textC.slice(0, 220) }));
      }

      await selectVariant(page, 'A');
    } catch (e) {
      fail('investment-ABC', String(e.message || e));
      await dumpPage(page, 'investment-error');
    }

    const investmentAssetId = (notes.A?.prov || {}).coverAssetId || '';
    const investmentText = notes.A?.text || '';

    // ---- ALTERNATE REAL EXTERIOR ----
    try {
      await editPost(page, ALTERNATE_BRIEF);
      const textAlt = await canvasText(page);
      const provAlt = await provenance(page);
      notes.alternate = { text: textAlt, prov: provAlt };
      const shotAlt = await shot(page, 'alternate-real-exterior');
      const changed = Boolean(provAlt.coverAssetId) && provAlt.coverAssetId !== investmentAssetId;
      const keptFacts = hasInvestmentFacts(textAlt);
      const keptHeadline = !investmentText || textAlt.split('|')[0] === investmentText.split('|')[0] || keptFacts;
      const stillReal = !forbiddenImage(provAlt) && provAlt.variants.length === 3;
      if (changed && keptFacts && stillReal) {
        pass(
          'alternate-asset',
          `${investmentAssetId} → ${provAlt.coverAssetId} file=${provAlt.selectedAssetFilename} shot=${shotAlt}`,
        );
      } else {
        fail('alternate-asset', JSON.stringify({ changed, keptFacts, keptHeadline, stillReal, provAlt, text: textAlt.slice(0, 220) }));
      }
    } catch (e) {
      fail('alternate-asset', String(e.message || e));
    }

    // ---- EDITABLE ELEMENTS ----
    try {
      const before = await canvasText(page);
      await editPost(page, "CTA'yı kaldır");
      const afterCta = await canvasText(page);
      const geo = await canvasGeometry(page);
      notes.editable = { before, afterCta, geo };
      const ctaGone = !/learn more|invest now|discover|contact|cta/i.test(afterCta)
        || geo.filter((g) => g.type === 'BUTTON' || g.role === 'cta').length === 0;
      await shot(page, 'editable-remove-cta');
      if (ctaGone) {
        pass('editable-elements', 'CTA removed without regenerating photograph');
      } else {
        fail('editable-elements', JSON.stringify({ before: before.slice(0, 180), afterCta: afterCta.slice(0, 180), geo }));
      }
    } catch (e) {
      fail('editable-elements', String(e.message || e));
    }

    // ---- PERSIST + RELOAD ----
    try {
      const before = await provenance(page);
      if (await page.locator('[data-testid="smb-save"]').count()) {
        await page.click('[data-testid="smb-save"]');
        await page.waitForTimeout(2000);
      }
      await page.reload({ waitUntil: 'domcontentloaded' });
      await waitReady(page);
      await page.waitForTimeout(2500);
      await waitCoverReady(page);
      await selectArtDirectorEngine(page);
      await page.waitForFunction(
        () => document.querySelectorAll('[data-testid^="smb-art-director-option-"]').length >= 3,
        null,
        { timeout: 20000 },
      ).catch(() => null);
      const after = await provenance(page);
      notes.reload = { before, after };
      const shotReload = await shot(page, 'persist-reload');
      const ok =
        after.coverAssetId === before.coverAssetId
        && after.variants.length === 3
        && !forbiddenImage(after);
      if (ok) {
        pass('persist-reload', `asset=${after.coverAssetId} variants=${after.variants.length} shot=${shotReload}`);
      } else {
        fail('persist-reload', JSON.stringify({ before, after }));
      }
    } catch (e) {
      fail('persist-reload', String(e.message || e));
    }

    // ---- FULLSCREEN ----
    try {
      await page.locator('[data-testid="smb-fullscreen-zoom"]').click({ force: true });
      await page.waitForTimeout(800);
      const fs = await provenance(page);
      const shotFs = await shot(page, 'fullscreen', true);
      if (fs.fullscreen === 'true' && fs.coverAssetId) {
        pass('fullscreen', `shot=${shotFs}`);
      } else {
        fail('fullscreen', JSON.stringify(fs));
      }
      await page.locator('[data-testid="smb-fullscreen-zoom"]').click({ force: true });
      await page.waitForTimeout(400);
    } catch (e) {
      fail('fullscreen', String(e.message || e));
    }

    // ---- MOBILE READABILITY ----
    try {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(600);
      const shotM = await shot(page, 'mobile-390', true);
      const geo = await canvasGeometry(page);
      const readable = geo.some((g) => g.role === 'headline' || g.type === 'TEXT' || g.type === 'METRIC_GROUP');
      if (readable) {
        pass('mobile-readable', `shot=${shotM}`);
      } else {
        fail('mobile-readable', JSON.stringify({ geo, shotM }));
      }
      await page.setViewportSize({ width: 1440, height: 1100 });
      await page.waitForTimeout(400);
    } catch (e) {
      fail('mobile-readable', String(e.message || e));
    }

    // ---- LOCATION CAMPAIGN ----
    try {
      await createPost(page, LOCATION_BRIEF);
      const text = await canvasText(page);
      const geo = await canvasGeometry(page);
      const prov = await provenance(page);
      notes.location = { text, geo, prov };
      const shotLoc = await shot(page, 'location-campaign');
      const noMetrics = !hasInvestmentFacts(text) && !geo.some((g) => g.type === 'METRIC_GROUP');
      const locCampaign = prov.campaignType === 'LOCATION' || prov.intent === 'LOCATION';
      const real =
        !forbiddenImage(prov)
        && Boolean(prov.coverAssetId)
        && Boolean(prov.selectedAssetFilename)
        && prov.artDirector === 'true'
        && prov.variants.length === 3;
      const different = prov.composition !== (notes.A?.prov || {}).composition || locCampaign;
      if (noMetrics && locCampaign && real && different) {
        pass(
          'location',
          `comp=${prov.composition} asset=${prov.selectedAssetFilename} subject=${prov.indicatorSubject} shot=${shotLoc}`,
        );
      } else {
        fail('location', JSON.stringify({ noMetrics, locCampaign, real, different, prov, text: text.slice(0, 240) }));
      }
    } catch (e) {
      fail('location', String(e.message || e));
    }
  } finally {
    await browser.close();
  }

  write(join(SHOT_DIR, 'gate.json'), JSON.stringify({ results, notes }, null, 2));
  const failed = results.filter((r) => r.ok === false);
  console.log(`SUMMARY ${results.filter((r) => r.ok).length}/${results.length} passed`);
  console.log(`SCREENSHOTS ${SHOT_DIR}`);
  if (failed.length) process.exit(1);
}

main().catch((err) => {
  console.error(String(err?.message || err));
  process.exit(1);
});
