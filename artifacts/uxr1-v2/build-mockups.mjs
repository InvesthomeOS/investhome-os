/**
 * UXR1 V2 — generate hi-fi HTML frames + capture PNGs.
 * Usage: node artifacts/uxr1-v2/build-mockups.mjs
 * Requires: playwright (uses ../../.pw-verify or artifacts/bi-g14 node_modules if present)
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRAMES = path.join(__dirname, 'mockups', 'frames');
const OUT = path.join(__dirname, 'mockups');
const REVIEW_MOCKUPS = path.join(__dirname, '..', 'uxr1-simplification', 'review', 'mockups');

const css = `
:root {
  --canvas: #f8fafc;
  --surface: #ffffff;
  --navy: #0f2744;
  --navy-soft: #e8eef5;
  --blue: #2563eb;
  --blue-soft: #eff6ff;
  --gray-200: #e2e8f0;
  --gray-500: #64748b;
  --gray-700: #334155;
  --radius: 16px;
  --shadow: 0 1px 2px rgba(15,39,68,.04), 0 6px 20px rgba(15,39,68,.07);
  --font: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font); background: #cbd5e1; color: var(--navy); }
.app {
  width: 1440px; min-height: 900px; margin: 0 auto; background: var(--canvas);
  display: grid; grid-template-columns: 220px 1fr; box-shadow: 0 20px 50px rgba(15,39,68,.18);
}
.side { background: var(--surface); border-right: 1px solid var(--gray-200); padding: 20px 14px; }
.logo { font-weight: 800; letter-spacing: .06em; font-size: 12px; color: var(--navy); padding: 4px 10px 18px; }
.nav a {
  display: block; padding: 9px 12px; border-radius: 10px; color: var(--gray-500);
  text-decoration: none; font-size: 13px; font-weight: 500; margin-bottom: 2px;
}
.nav a.on { background: var(--blue-soft); color: var(--blue); font-weight: 700; }
.main { padding: 22px 28px 36px; }
.top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.top h1 { font-size: 22px; font-weight: 700; }
.top .meta { font-size: 12px; color: var(--gray-500); }
.chip {
  display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600;
  padding: 5px 10px; border-radius: 999px; background: var(--navy-soft); color: var(--navy);
}
.grid { display: grid; gap: 14px; }
.g4 { grid-template-columns: repeat(4, 1fr); }
.g3 { grid-template-columns: repeat(3, 1fr); }
.g2 { grid-template-columns: 1.2fr 1fr; }
.g21 { grid-template-columns: 1fr 1fr; }
.card {
  background: var(--surface); border: 1px solid var(--gray-200); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 16px 18px;
}
.card h3 { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--gray-500); margin-bottom: 10px; }
.kpi .v { font-size: 26px; font-weight: 800; color: var(--navy); }
.kpi .d { font-size: 12px; color: var(--blue); font-weight: 600; margin-top: 4px; }
.bar { height: 10px; background: var(--gray-200); border-radius: 6px; margin: 8px 0; overflow: hidden; }
.bar > i { display: block; height: 100%; background: var(--blue); border-radius: 6px; }
.funnel div { display: flex; align-items: center; gap: 10px; margin: 8px 0; font-size: 12px; }
.funnel .t { height: 28px; background: linear-gradient(90deg, var(--navy), var(--blue)); border-radius: 6px; color: #fff; display: flex; align-items: center; padding: 0 10px; font-weight: 700; }
.list { display: flex; flex-direction: column; gap: 8px; }
.row {
  display: flex; justify-content: space-between; gap: 10px; align-items: center;
  padding: 10px 12px; border: 1px solid var(--gray-200); border-radius: 12px; background: #fff;
  font-size: 13px;
}
.btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border-radius: 10px;
  border: 1px solid var(--gray-200); background: #fff; font-size: 12px; font-weight: 600; color: var(--navy);
}
.btn.primary { background: var(--blue); color: #fff; border-color: var(--blue); }
.btn.ai { background: #f5f3ff; color: #5b4b8a; border-color: #ddd6fe; }
.cols { display: flex; gap: 12px; overflow: hidden; }
.col {
  flex: 1; min-width: 0; border: 1px solid var(--gray-200); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 10px; display: flex; flex-direction: column; gap: 10px;
}
.col.lead { background: #f0f7ff; }
.col.qualify { background: #eef8f4; }
.col.proposal { background: #f5f3ff; }
.col.nego { background: #fff7ed; }
.col.won { background: #ecfdf5; }
.col-h { display: flex; justify-content: space-between; font-size: 12px; font-weight: 800; color: var(--navy); }
.deal {
  background: #fff; border: 1px solid var(--gray-200); border-radius: 12px; padding: 12px;
  box-shadow: var(--shadow); font-size: 12px;
}
.deal strong { display: block; font-size: 13px; margin-bottom: 4px; }
.units { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.unit {
  background: #fff; border: 1px solid var(--gray-200); border-radius: var(--radius);
  box-shadow: var(--shadow); overflow: hidden;
}
.unit .media {
  aspect-ratio: 3/4; background: linear-gradient(160deg, #f2f6fa, #eff6ff);
  position: relative;
}
.badge {
  position: absolute; top: 10px; left: 10px; background: #fef3c7; color: #92400e;
  font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 8px;
}
.unit .body { padding: 14px; }
.unit .code { font-weight: 800; margin-bottom: 8px; }
.specs { display: grid; grid-template-columns: repeat(3,1fr); gap: 6px; font-size: 11px; color: var(--gray-500); margin-bottom: 8px; }
.specs b { display: block; color: var(--navy); font-size: 13px; }
.price { font-size: 18px; font-weight: 800; }
.rent { font-size: 12px; color: var(--gray-500); margin-top: 4px; }
.proj-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.proj .hero { height: 140px; background: linear-gradient(135deg, #1a3a5c, #2563eb); border-radius: 12px 12px 0 0; }
.proj .body { padding: 14px; }
.actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.prog { margin-top: 10px; }
.prog label { display: flex; justify-content: space-between; font-size: 11px; color: var(--gray-500); margin-bottom: 4px; }
.detail { display: grid; grid-template-columns: 1fr 320px; gap: 14px; }
.rail { display: flex; flex-direction: column; gap: 12px; }
.rail .card { padding: 14px; }
.map-stub {
  height: 180px; border: 1px dashed #cbd5e1; border-radius: 12px; background: #f1f5f9;
  display: grid; place-items: center; color: var(--gray-500); font-size: 12px; font-weight: 600;
}
.map-tools { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.channels { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.ch { font-size: 12px; }
.ch .n { font-weight: 800; margin-bottom: 8px; }
.metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; color: var(--gray-500); }
.metrics b { color: var(--navy); }
.advisor { border-left: 3px solid var(--blue); }
.studio-top { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.tab { padding: 8px 12px; border-radius: 10px; border: 1px solid var(--gray-200); background: #fff; font-size: 12px; font-weight: 600; }
.tab.on { background: var(--navy); color: #fff; border-color: var(--navy); }
.flow { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 12px 0; font-size: 12px; }
.flow span { background: var(--blue-soft); color: var(--blue); font-weight: 700; padding: 8px 10px; border-radius: 8px; }
.timeline .item { padding: 10px 0; border-bottom: 1px solid var(--gray-200); font-size: 13px; }
.timeline .item:last-child { border-bottom: 0; }
.muted { color: var(--gray-500); font-size: 12px; }
.tag { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--blue); margin-bottom: 6px; }
`;

function shell(active, title, body, subtitle = 'UXR1 V2 · Final PO decisions') {
  const items = [
    ['Dashboard', '04'],
    ['Customers', '05'],
    ['Sales', '06'],
    ['Inventory', '07'],
    ['Projects', '08'],
    ['Marketing', '10'],
    ['Content', '11'],
  ];
  return `<!DOCTYPE html><html lang="en" data-ds-version="v2"><head><meta charset="utf-8"/><title>${title}</title><style>${css}</style></head><body>
<div class="app" id="frame">
  <aside class="side">
    <div class="logo">INVESTHOME OS</div>
    <nav class="nav">
      ${items.map(([label, key]) => `<a class="${active === key ? 'on' : ''}" href="#">${label}</a>`).join('')}
      <a href="#" style="opacity:.45">Reports</a>
      <a href="#" style="opacity:.45">Finance</a>
    </nav>
  </aside>
  <main class="main">
    <div class="top">
      <div>
        <div class="chip">V2 · White / Navy / Blue / Gray · No dark mode</div>
        <h1 style="margin-top:10px">${title}</h1>
        <div class="meta">${subtitle}</div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="btn">Search</button>
        <button class="btn primary">Quick add</button>
      </div>
    </div>
    ${body}
  </main>
</div>
</body></html>`;
}

const screens = {
  '04-dashboard': shell('04', 'Dashboard', `
    <div class="grid g4" style="margin-bottom:14px">
      ${[['New leads','12','↑ 3'],['Follow-ups','8','3 overdue'],['Tasks due','5','Today'],['Meetings','3','2 virtual']].map(([l,v,d]) => `
        <div class="card kpi"><div class="muted">${l}</div><div class="v">${v}</div><div class="d">${d}</div></div>`).join('')}
    </div>
    <div class="grid g2" style="margin-bottom:14px">
      <div class="card"><h3>Sales funnel</h3>
        <div class="funnel">
          <div><div class="t" style="width:100%">Lead · 48</div></div>
          <div><div class="t" style="width:78%">Qualify · 31</div></div>
          <div><div class="t" style="width:55%">Proposal · 18</div></div>
          <div><div class="t" style="width:32%">Negotiation · 9</div></div>
        </div>
      </div>
      <div class="card"><h3>Unit availability</h3>
        <div style="height:140px;display:grid;place-items:center;border-radius:12px;background:var(--blue-soft);font-weight:800;color:var(--navy)">Available 42% · Reserved 21% · Sold 37%</div>
      </div>
    </div>
    <div class="grid g21" style="margin-bottom:14px">
      <div class="card"><h3>Monthly sales</h3>
        <div class="bar"><i style="width:42%"></i></div>
        <div class="bar"><i style="width:68%"></i></div>
        <div class="bar"><i style="width:81%"></i></div>
      </div>
      <div class="card"><h3>Active projects</h3>
        <div class="list">
          <div class="row"><span>North Towers</span><strong>72%</strong></div>
          <div class="row"><span>Marina Residences</span><strong>41%</strong></div>
        </div>
      </div>
    </div>
    <div class="card"><h3>Follow-ups</h3>
      <div class="list">
        <div class="row"><span>Ada Yılmaz — Proposal sent</span><button class="btn primary">Open</button></div>
        <div class="row"><span>M. Kaya — Qualify call</span><button class="btn">Open</button></div>
      </div>
    </div>`),

  '05-customer-profile': shell('05', 'Customer profile · Ada Yılmaz', `
    <div class="grid g2">
      <div>
        <div class="card" style="margin-bottom:14px">
          <div class="tag">Quick actions</div>
          <div class="actions">
            <button class="btn primary">Call</button>
            <button class="btn">Email</button>
            <button class="btn">WhatsApp</button>
            <button class="btn">Schedule</button>
            <button class="btn ai">AI brief</button>
          </div>
        </div>
        <div class="card">
          <div class="tag">Journey timeline · primary activity</div>
          <div class="timeline">
            <div class="item"><strong>Proposal sent</strong><div class="muted">Today · North Towers A-1204</div></div>
            <div class="item"><strong>Site visit</strong><div class="muted">Mon · Prefer high floor, sea view</div></div>
            <div class="item"><strong>Lead created</strong><div class="muted">Website · Instagram campaign</div></div>
          </div>
        </div>
      </div>
      <div>
        <div class="card" style="margin-bottom:14px">
          <div class="tag">Opportunity</div>
          <div class="kpi"><div class="v">$428k</div><div class="d">Stage: Proposal · 62% win</div></div>
        </div>
        <div class="card">
          <div class="tag">Preferences</div>
          <div class="list">
            <div class="row"><span>Beds</span><strong>2–3</strong></div>
            <div class="row"><span>Budget</span><strong>$350–450k</strong></div>
            <div class="row"><span>Must</span><strong>Parking · Sea view</strong></div>
          </div>
        </div>
      </div>
    </div>`),

  '06-sales-pipeline': shell('06', 'Sales pipeline', `
    <div class="grid g4" style="margin-bottom:14px">
      ${[['Open pipeline','$4.2M'],['Weighted','$1.8M'],['Closing 14d','6'],['Stalled','4']].map(([l,v]) => `
        <div class="card kpi"><div class="muted">${l}</div><div class="v" style="font-size:22px">${v}</div></div>`).join('')}
    </div>
    <div class="cols">
      ${[
        ['lead','Lead','2',[['Selin A.','$210k'],['R. Demir','$180k']]],
        ['qualify','Qualify','2',[['Nova LLC','$620k'],['H. Öz','$240k']]],
        ['proposal','Proposal','1',[['Ada Y.','$428k']]],
        ['nego','Negotiation','1',[['Park Co.','$910k']]],
        ['won','Won','1',[['Blue Fund','$1.1M']]],
      ].map(([tone,title,count,deals]) => `
        <div class="col ${tone}">
          <div class="col-h"><span>${title}</span><span>${count}</span></div>
          ${deals.map(([n,v]) => `<div class="deal"><strong>${n}</strong><div class="muted">Next: follow-up</div><div style="margin-top:6px;font-weight:800">${v}</div></div>`).join('')}
        </div>`).join('')}
    </div>`),

  '07-inventory': shell('07', 'Inventory', `
    <div class="units">
      ${[
        ['A-1204','2','2','1,140','$428,000','$2,150','-4%'],
        ['B-0802','1','1','780','$265,000','$1,450','Hot'],
        ['C-1501','3','2','1,520','$612,000','$2,900','-6%'],
        ['D-0305','2','1','980','$339,000','$1,780','AI match'],
      ].map(([code,beds,baths,sqft,price,rent,badge]) => `
        <div class="unit">
          <div class="media"><span class="badge">${badge}</span></div>
          <div class="body">
            <div class="code">${code}</div>
            <div class="specs"><div>Beds<b>${beds}</b></div><div>Baths<b>${baths}</b></div><div>Sqft<b>${sqft}</b></div></div>
            <div class="price">${price}</div>
            <div class="rent">Est. rent ${rent}</div>
          </div>
        </div>`).join('')}
    </div>`),

  '08-project-cards': shell('08', 'Projects', `
    <div class="proj-grid">
      ${[['North Towers','72','58'],['Marina Residences','41','33'],['Garden Court','88','71']].map(([name,c,s]) => `
        <div class="card proj" style="padding:0;overflow:hidden">
          <div class="hero"></div>
          <div class="body">
            <strong style="font-size:16px">${name}</strong>
            <div class="prog">
              <label><span>Construction</span><span>${c}%</span></label>
              <div class="bar"><i style="width:${c}%;background:var(--navy)"></i></div>
              <label><span>Sales</span><span>${s}%</span></label>
              <div class="bar"><i style="width:${s}%"></i></div>
            </div>
            <div class="actions">
              <button class="btn">Share</button>
              <button class="btn">Email</button>
              <button class="btn">WhatsApp</button>
              <button class="btn primary">Generate proposal</button>
              <button class="btn ai">AI summary</button>
            </div>
          </div>
        </div>`).join('')}
    </div>`),

  '09-project-detail': shell('08', 'Project detail · North Towers', `
    <div class="detail">
      <div>
        <div class="card" style="margin-bottom:14px">
          <div class="tag">Overview</div>
          <div class="grid g21">
            <div><div class="muted">Units</div><div class="v" style="font-size:22px;font-weight:800">186</div></div>
            <div><div class="muted">Sold</div><div class="v" style="font-size:22px;font-weight:800">58%</div></div>
          </div>
        </div>
        <div class="card" style="margin-bottom:14px">
          <div class="tag">Location intelligence</div>
          <div class="map-tools">
            <button class="btn">Zoom</button><button class="btn">Satellite</button>
            <button class="btn">Street view</button><button class="btn">Directions</button><button class="btn">Nearby</button>
          </div>
          <div class="map-stub">Map provider stub · interactive (zoom / satellite / street / nearby)</div>
          <div class="grid g3" style="margin-top:12px">
            <div class="card" style="box-shadow:none"><div class="muted">Walk</div><strong>86</strong></div>
            <div class="card" style="box-shadow:none"><div class="muted">Transit</div><strong>74</strong></div>
            <div class="card" style="box-shadow:none"><div class="muted">Bike</div><strong>69</strong></div>
          </div>
          <p class="muted" style="margin-top:10px">AI Neighborhood Summary (editable): Quiet waterfront pocket with strong café density and metro access within 8 minutes…</p>
        </div>
        <div class="card">
          <div class="tag">Market intelligence · provider-agnostic</div>
          <div class="grid g21">
            <div><div class="muted">Median sale</div><strong>$412k</strong></div>
            <div><div class="muted">Median rent</div><strong>$2,050</strong></div>
          </div>
          <p class="muted" style="margin-top:10px">Comps sales/rentals · rental & price trends · neighborhood stats · AI Market Summary (editable). Not vendor-locked.</p>
        </div>
      </div>
      <div class="rail">
        <div class="muted" style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em">Configurable widgets · drag order</div>
        ${['Budget','Documents','Risks','AI Insights','Activity','Investors','Tasks'].map((w,i)=>`
          <div class="card"><strong>${i+1}. ${w}</strong><div class="muted">Admin-configurable · drag-drop</div></div>`).join('')}
      </div>
    </div>`),

  '10-marketing-home': shell('10', 'Marketing control center', `
    <div class="channels" style="margin-bottom:14px">
      ${[
        ['Website','$0','128','18','—'],
        ['SEO','$1.2k','64','9','4.1x'],
        ['Email','$0.4k','92','21','6.2x'],
        ['Instagram','$3.1k','210','33','2.8x'],
        ['Facebook','$2.4k','150','22','2.1x'],
        ['LinkedIn','$1.8k','48','11','3.0x'],
        ['Google Ads','$6.5k','310','41','2.4x'],
        ['Meta Ads','$5.2k','280','37','2.2x'],
        ['YouTube','$2.0k','76','8','1.6x'],
      ].map(([n,spend,leads,conv,roi]) => `
        <div class="card ch">
          <div class="n">${n}</div>
          <div class="metrics">
            <div>Spend<br/><b>${spend}</b></div>
            <div>Leads<br/><b>${leads}</b></div>
            <div>Conv.<br/><b>${conv}</b></div>
            <div>ROI<br/><b>${roi}</b></div>
          </div>
          <div class="muted" style="margin-top:8px">Campaign performance · healthy</div>
        </div>`).join('')}
    </div>
    <div class="card advisor">
      <div class="tag">AI Marketing Advisor · editable · never forced</div>
      <div class="list">
        <div class="row"><span>Pause underperforming YouTube set · reallocate $800 to SEO</span><button class="btn">Edit</button></div>
        <div class="row"><span>Publish Instagram carousel from North Towers gallery</span><button class="btn">Edit</button></div>
        <div class="row"><span>Repurpose email #14 into LinkedIn post</span><button class="btn">Dismiss</button></div>
      </div>
    </div>`),

  '11-content-studio': shell('11', 'Content studio', `
    <div class="studio-top">
      <span class="tab">Blog</span><span class="tab">Social</span><span class="tab">Email</span>
      <span class="tab on">Landing pages</span>
      <span style="flex:1"></span>
      <button class="btn ai">Create with AI</button>
      <button class="btn primary">Create manually</button>
    </div>
    <div class="card" style="margin-bottom:14px">
      <div class="tag">Workflow · always editable</div>
      <div class="flow">
        <span>AI Generate</span>→<span>Human Edit</span>→<span>AI Improve</span>→<span>Human Approve</span>→<span>Publish</span>
      </div>
      <p class="muted">Future agents (Writing / Design / SEO / Brand / Compliance / Media) plug in via extension points — no UI rewrite.</p>
    </div>
    <div class="grid g21">
      <div class="card">
        <h3>Drafts</h3>
        <div class="list">
          <div class="row"><span>North Towers — Launch LP</span><strong>Human edit</strong></div>
          <div class="row"><span>Marina — Investor LP</span><strong>AI improve</strong></div>
        </div>
      </div>
      <div class="card">
        <h3>Data reuse</h3>
        <p class="muted">Canonical project media + specs feed website, landing, brochures, presentations, email, WhatsApp, and AI content.</p>
      </div>
    </div>`),
};

fs.mkdirSync(FRAMES, { recursive: true });
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(REVIEW_MOCKUPS, { recursive: true });

for (const [id, html] of Object.entries(screens)) {
  fs.writeFileSync(path.join(FRAMES, `${id}.html`), html, 'utf8');
}
console.log('Wrote', Object.keys(screens).length, 'HTML frames');

const require = createRequire(import.meta.url);

function loadPlaywright() {
  const candidates = [
    path.join(__dirname, '..', '..', '.pw-verify', 'node_modules', 'playwright'),
    path.join(__dirname, '..', 'bi-g14', 'node_modules', 'playwright'),
  ];
  for (const c of candidates) {
    try {
      return require(c);
    } catch {
      /* try next */
    }
  }
  throw new Error('playwright not found — install in .pw-verify or artifacts/bi-g14');
}

function serveStatic(root) {
  return createServer((req, res) => {
    const url = new URL(req.url || '/', 'http://127.0.0.1');
    let file = path.join(root, decodeURIComponent(url.pathname));
    if (url.pathname === '/') file = path.join(root, '04-dashboard.html');
    if (!file.startsWith(root) || !fs.existsSync(file)) {
      res.writeHead(404); res.end('missing'); return;
    }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(fs.readFileSync(file));
  });
}

const server = serveStatic(FRAMES);
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const { port } = server.address();
const base = `http://127.0.0.1:${port}`;

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 920 }, deviceScaleFactor: 1 });

const map = {
  '04-dashboard': '04-dashboard-desktop.png',
  '05-customer-profile': '05-customer-profile-desktop.png',
  '06-sales-pipeline': '06-sales-pipeline-desktop.png',
  '07-inventory': '07-inventory-desktop.png',
  '08-project-cards': '08-project-cards-desktop.png',
  '09-project-detail': '09-project-detail-desktop.png',
  '10-marketing-home': '10-marketing-home-desktop.png',
  '11-content-studio': '11-content-studio-desktop.png',
};

for (const [id, png] of Object.entries(map)) {
  await page.goto(`${base}/${id}.html`, { waitUntil: 'networkidle' });
  const frame = page.locator('#frame');
  const outV2 = path.join(OUT, png);
  const outReview = path.join(REVIEW_MOCKUPS, png);
  await frame.screenshot({ path: outV2, type: 'png' });
  fs.copyFileSync(outV2, outReview);
  const size = fs.statSync(outV2).size;
  console.log('OK', png, size);
}

await browser.close();
server.close();
console.log('Done. PNGs in artifacts/uxr1-v2/mockups and review/mockups');
