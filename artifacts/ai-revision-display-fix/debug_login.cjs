const { chromium } = require('C:/Users/eminb/Projects/investhome-os/.pw-verify/node_modules/playwright');

(async () => {
  const b = await chromium.launch({ headless: true, channel: 'msedge' });
  const p = await b.newPage();
  p.on('response', async (r) => {
    const u = r.url();
    if (u.includes('/auth/') || u.includes('login')) {
      let body = '';
      try {
        body = (await r.text()).slice(0, 300);
      } catch {}
      console.log('RESP', r.status(), u, body);
    }
  });
  await p.goto('http://127.0.0.1:3000/login', { waitUntil: 'domcontentloaded' });
  await p.locator('input[type="email"]').fill('superadmin@investhome.demo');
  await p.locator('input[type="password"]').fill('Investhome2026!');
  await p.getByRole('button', { name: 'Giriş Yap' }).click();
  await p.waitForTimeout(6000);
  console.log('final', p.url());
  const toast = await p.locator('body').innerText();
  console.log('body_snip', toast.slice(0, 500));
  await p.screenshot({ path: 'artifacts/ai-revision-display-fix/login-fail.png' });
  await b.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
