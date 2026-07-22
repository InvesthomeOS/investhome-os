import { chromium } from 'playwright';
import fs from 'fs';
const out = [];
const browser = await chromium.launch({headless:true});
const page = await browser.newPage();
page.on('console', m => { if (m.type()==='error') out.push('console:'+m.text()); });
page.on('pageerror', e => out.push('pageerror:'+String(e)));
try {
  await page.goto('http://localhost:3000/portal/login', {waitUntil:'networkidle', timeout:60000});
  await page.fill('[data-testid=portal-login-email]', 'investor.a@investhome.demo');
  await page.fill('[data-testid=portal-login-password]', 'Portal123!');
  await Promise.all([
    page.waitForNavigation({waitUntil:'domcontentloaded', timeout:30000}).catch(()=>null),
    page.click('[data-testid=portal-login-submit']),
  ]);
  await page.waitForTimeout(2500);
  out.push('url='+page.url());
  out.push('status-body='+(await page.locator('body').innerText()).slice(0,300).replace(/\n/g,' | '));
  await page.screenshot({path:'../artifacts/g10-readiness/screenshots/portal-after-login-debug.png'});
  for (const r of ['/portal/portfolio','/portal/documents','/portal/account']) {
    try {
      const res = await page.goto('http://localhost:3000'+r, {waitUntil:'domcontentloaded', timeout:30000});
      out.push(r+' => '+res?.status()+' '+page.url());
      await page.screenshot({path:'../artifacts/g10-readiness/screenshots/portal-'+r.replace(/\//g,'_')+'.png'});
    } catch (e) {
      out.push(r+' ERROR '+String(e).slice(0,200));
    }
  }
} catch (e) {
  out.push('FATAL '+String(e));
}
fs.writeFileSync('../artifacts/g10-readiness/logs/portal-smoke.txt', out.join('\n'));
console.log(out.join('\n'));
await browser.close();
