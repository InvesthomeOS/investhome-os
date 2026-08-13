/**
 * Live Creative Direction Engine tests A–E on The Temple.
 * Does not print secrets. Run: node scripts/smb-creative-direction-live.mjs
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
const SHOT_DIR = join(__dirname, '..', 'artifacts', 'smb-creative-direction');

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

async function canvasText(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[data-testid^="smb-el-"]')];
    return nodes
      .map((n) => (n.textContent || '').trim())
      .filter(Boolean)
      .join(' | ');
  });
}

async function creativeDebug(page) {
  return page.evaluate(() => {
    const el = document.querySelector('[data-testid="smb-workspace"]');
    if (!el) return {};
    return {
      intent: el.getAttribute('data-creative-intent') || '',
      direction: el.getAttribute('data-creative-direction') || '',
      composition: el.getAttribute('data-creative-composition') || '',
      density: el.getAttribute('data-creative-density') || '',
      contrast: el.getAttribute('data-creative-contrast') || '',
      cta: el.getAttribute('data-creative-cta') || '',
      quality: el.getAttribute('data-creative-quality') || '',
    };
  });
}

async function overlayToken(page) {
  return page.evaluate(() => document.querySelector('.smb-ws__artboard-overlay')?.getAttribute('data-overlay') || '');
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

async function createPost(page, prompt) {
  await page.fill('[data-testid="smb-ai-design-input"]', prompt);
  await page.click('[data-testid="smb-ai-design-submit"]');
  await waitAiIdle(page);
  await page.waitForTimeout(2500);
  for (let i = 0; i < 8; i++) {
    const ready = await page.evaluate(() => {
      const img = document.querySelector('[data-testid="smb-artboard"] img');
      return Boolean(img && img.complete && img.naturalWidth > 0);
    });
    if (ready) break;
    await page.waitForTimeout(500);
  }
}

async function editPost(page, prompt) {
  await page.fill('[data-testid="smb-ai-design-input"]', prompt);
  await page.click('[data-testid="smb-ai-design-edit"]');
  await waitAiIdle(page);
  await page.waitForTimeout(800);
}

async function shot(page, name) {
  mkdir(SHOT_DIR, { recursive: true });
  const file = join(SHOT_DIR, `${name}.png`);
  const art = page.locator('[data-testid="smb-artboard"]');
  if (await art.count()) {
    await art.screenshot({ path: file });
  } else {
    await page.screenshot({ path: file, fullPage: false });
  }
  return file;
}

function inventedLocation(text) {
  const t = (text || '').toLowerCase();
  return (
    t.includes('minute walk') ||
    t.includes('dakika yürü') ||
    t.includes('2 min') ||
    t.includes('walking distance to') ||
    /\b\d+\s*min(ute)?s?\s*walk/.test(t)
  );
}

async function main() {
  mkdir(SHOT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on('pageerror', (err) => console.log('PAGEERROR', err.message));
  const directions = {};

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
      }
    }

    // ---- TEST A: Location — designed, not template-filled ----
    try {
      await createPost(
        page,
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium bir Instagram kare postu hazırla. Proje verilerini kullan. En uygun gerçek proje görselini seç. İngilizce hazırla.",
      );
      const text = await canvasText(page);
      const dbg = await creativeDebug(page);
      const overlay = await overlayToken(page);
      directions.A = dbg;
      const shotPath = await shot(page, 'test-a-location');
      const hasHeadline = /washington|columbia|central|address|temple|city/i.test(text);
      const noInvented = !inventedLocation(text);
      const noIrr = !/%\s*14|14%|\$500/.test(text);
      const designed = Boolean(dbg.direction && dbg.composition);
      if (hasHeadline && noInvented && noIrr && designed) {
        pass('A', `dir=${dbg.direction} comp=${dbg.composition} overlay=${overlay} shot=${shotPath}`);
      } else {
        fail('A', JSON.stringify({ dbg, overlay, text: text.slice(0, 220), hasHeadline, noInvented, noIrr }));
      }
    } catch (e) {
      fail('A', String(e.message || e));
    }

    const locA = (await creativeDebug(page)).composition;

    // ---- TEST B: Investment — claim-guard metrics only ----
    try {
      await createPost(
        page,
        'The Temple için yatırımcı odaklı premium Instagram kare postu. Minimum yatırım: $500,000 Hedef getiri: %14 Yatırım süresi: 24 ay. İngilizce hazırla.',
      );
      const text = await canvasText(page);
      const dbg = await creativeDebug(page);
      directions.B = dbg;
      const shotPath = await shot(page, 'test-b-investment');
      const hasMetrics = /\$500|500,000|14%|%14|24/.test(text);
      const dirOk = dbg.direction === 'INVESTMENT_DATA' || dbg.intent === 'INVESTMENT';
      if (hasMetrics && dirOk) {
        pass('B', `dir=${dbg.direction} comp=${dbg.composition} shot=${shotPath}`);
      } else {
        fail('B', JSON.stringify({ dbg, text: text.slice(0, 240), hasMetrics, dirOk }));
      }
    } catch (e) {
      fail('B', String(e.message || e));
    }

    // ---- TEST C: Architecture — building hero, restrained copy ----
    try {
      await createPost(
        page,
        'The Temple mimarisini öne çıkaran sakin, görsel ağırlıklı premium bir Instagram kare postu hazırla. İngilizce. Proje görselini kullan.',
      );
      const text = await canvasText(page);
      const dbg = await creativeDebug(page);
      directions.C = dbg;
      const shotPath = await shot(page, 'test-c-architecture');
      const noMetrics = !/\$500|14%|%14/.test(text);
      const restrained = (text.split('|').length <= 4);
      const dirOk = dbg.intent === 'ARCHITECTURE' || dbg.direction === 'ARCHITECTURAL_FEATURE';
      if (noMetrics && restrained && dirOk) {
        pass('C', `dir=${dbg.direction} dens=${dbg.density} cta=${dbg.cta} shot=${shotPath}`);
      } else {
        fail('C', JSON.stringify({ dbg, text: text.slice(0, 240), noMetrics, restrained, dirOk }));
      }
    } catch (e) {
      fail('C', String(e.message || e));
    }

    // ---- TEST D: Lifestyle — aspirational, no invented amenities ----
    try {
      await createPost(
        page,
        "The Temple yaşam atmosferini anlatan premium Instagram kare postu hazırla. İngilizce. Proje görselini kullan. Olmayan olanakları uydurma.",
      );
      const text = await canvasText(page);
      const dbg = await creativeDebug(page);
      directions.D = dbg;
      const shotPath = await shot(page, 'test-d-lifestyle');
      const inventedAmenity = /infinity pool|helipad|private beach|ski-in/i.test(text);
      const dirOk = dbg.intent === 'LIFESTYLE' || dbg.direction === 'LIFESTYLE_PREMIUM' || dbg.direction === 'EDITORIAL_LUXURY';
      if (!inventedAmenity && dirOk) {
        pass('D', `dir=${dbg.direction} comp=${dbg.composition} shot=${shotPath}`);
      } else {
        fail('D', JSON.stringify({ dbg, text: text.slice(0, 240), inventedAmenity, dirOk }));
      }
    } catch (e) {
      fail('D', String(e.message || e));
    }

    // ---- TEST E: Variety + localized edit vs redesign ----
    try {
      await createPost(
        page,
        "The Temple'in Washington'daki konumunu anlatan ikinci bir premium Instagram kare postu hazırla. İngilizce.",
      );
      const dbg2 = await creativeDebug(page);
      const text2 = await canvasText(page);
      directions.E_location2 = dbg2;
      await shot(page, 'test-e-location-variety');
      const varied = !locA || dbg2.composition !== locA || dbg2.direction !== (directions.A?.direction || '');
      const headlineBefore = await page.evaluate(() => {
        const el = document.querySelector('[data-el-role="headline"]');
        return el ? (el.textContent || '').trim() : '';
      });
      await editPost(page, 'Başlığı biraz küçült');
      const headlineAfter = await page.evaluate(() => {
        const el = document.querySelector('[data-el-role="headline"]');
        return el ? (el.textContent || '').trim() : '';
      });
      const localized = headlineAfter === headlineBefore;
      await shot(page, 'test-e-localized-edit');
      await editPost(page, 'Bu postu tamamen yeniden tasarla.');
      const dbgRedesign = await creativeDebug(page);
      directions.E_redesign = dbgRedesign;
      await shot(page, 'test-e-redesign');
      if (varied && localized) {
        pass(
          'E',
          `variety ${locA}→${dbg2.composition}; localized edit kept copy; redesign dir=${dbgRedesign.direction}`,
        );
      } else {
        fail('E', JSON.stringify({ locA, second: dbg2, varied, localized, headlineBefore, headlineAfter, dbgRedesign, text2: text2.slice(0, 160) }));
      }
    } catch (e) {
      fail('E', String(e.message || e));
    }
  } finally {
    await browser.close();
  }

  write(join(SHOT_DIR, 'directions.json'), JSON.stringify({ results, directions }, null, 2));
  const failed = results.filter((r) => !r.ok);
  console.log(`SUMMARY ${results.filter((r) => r.ok).length}/${results.length} passed`);
  console.log(`SCREENSHOTS ${SHOT_DIR}`);
  if (failed.length) process.exit(1);
}

main().catch((err) => {
  console.error(String(err?.message || err));
  process.exit(1);
});
