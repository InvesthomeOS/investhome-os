import { createRequire } from "node:module";
import path from "node:path";
import fs from "node:fs";
const require = createRequire(import.meta.url);
const { chromium } = require(path.join(process.cwd(), ".pw-verify/node_modules/@playwright/test"));
const BASE = "http://localhost:3000";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
await page.locator('input[type="email"], input[name="email"]').first().fill("superadmin@investhome.demo");
await page.locator('input[type="password"]').first().fill("Demo123!");
await page.locator('button[type="submit"]').first().click();
await page.waitForURL(/dashboard/, { timeout: 45000 });
await page.goto(`${BASE}/dashboard/admin/platform/feature-flags`, { waitUntil: "networkidle" });
await page.locator("[data-platform-flags]").waitFor({ timeout: 30000 });
const keys = await page.locator("[data-flag-key]").evaluateAll(els => els.map(e => e.getAttribute("data-flag-key")));
console.log("FLAG_KEYS", keys);
const flagRow = page.locator('[data-flag-key="platform_admin"]');
console.log("platform_admin count", await flagRow.count());
if (await flagRow.count()) {
  await flagRow.click();
  await page.waitForTimeout(1500);
  const detail = page.locator("[data-flag-detail]");
  console.log("detail count", await detail.count());
  if (await detail.count()) {
    console.log("detail box", await detail.boundingBox());
    console.log("detail html len", (await detail.innerHTML()).length);
    console.log("detail text", JSON.stringify((await detail.innerText()).slice(0, 400)));
    await detail.screenshot({ path: "artifacts/ecosystem-g15a/_probe-06-detail.png" });
    await page.screenshot({ path: "artifacts/ecosystem-g15a/_probe-06-page.png", fullPage: true });
    console.log("detail shot", fs.statSync("artifacts/ecosystem-g15a/_probe-06-detail.png").size);
    console.log("page shot", fs.statSync("artifacts/ecosystem-g15a/_probe-06-page.png").size);
  } else {
    const box = await flagRow.boundingBox();
    console.log("row box", box);
  }
}
await browser.close();
