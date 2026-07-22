import fs from 'fs';
import path from 'path';

function tryWrite(p, content) {
  try {
    fs.writeFileSync(p, content, 'utf8');
    return true;
  } catch (e) {
    console.error('LOCK', p, e.code);
    fs.writeFileSync(p + '.v2-update', content, 'utf8');
    return false;
  }
}

const indexPath = 'artifacts/uxr1-simplification/review/index.html';
let index = fs.readFileSync(indexPath, 'utf8');
index = index
  .replaceAll('WAITING FOR FINAL PRODUCT REVIEW', 'V2 PO DECISIONS APPROVED')
  .replaceAll('NO IMPLEMENTATION', 'DS FOUNDATION ALLOWED · ROUTES PHASE 2')
  .replace('Simplification review — ready for product sign-off', 'UXR1 V2 — PO decisions consolidated')
  .replace(
    'Waiting for final product review — no implementation.',
    'V2 refine package: tokens + components + mockups + specs. Production route migration is Phase 2.',
  )
  .replace(
    '<span><strong>S3–11</strong> Pending product review</span>',
    '<span><strong>S04–11</strong> Approved (V2 refine)</span>',
  )
  .replace(
    '<span><strong>Implementation</strong> Blocked</span>',
    '<span><strong>Implementation</strong> Phase 0 foundation / Phase 2 routes</span>',
  );

index = index.replace(
  /href="(0[4-9]-[^"]+|1[01]-[^"]+)\.html"([\s\S]*?)<span class="badge pending">Pending<\/span>/g,
  'href="$1.html"$2<span class="badge ok">Approved</span>',
);
index = index.replace(
  /href="12-design-system-recommendations\.html"([\s\S]*?)<span class="badge pending">Pending<\/span>/,
  'href="12-design-system-recommendations.html"$1<span class="badge ok">V2 landed</span>',
);
index = index.replace(
  /href="13-implementation-roadmap\.html"([\s\S]*?)<span class="badge pending">Pending<\/span>/,
  'href="13-implementation-roadmap.html"$1<span class="badge pending">See V2 roadmap</span>',
);

if (!index.includes('artifacts/uxr1-v2')) {
  index = index.replace(
    '</header>',
    `<p class="lede" style="margin-top:12px"><strong>V2 package:</strong> <a href="../../uxr1-v2/REPORT.md">REPORT.md</a> ·
  <a href="../../uxr1-v2/README.md">artifacts/uxr1-v2</a> ·
  Design System <a href="../../../docs/design-system/investhome-os-design-system-v2.md">V2</a></p>
</header>`,
  );
}
console.log('index write', tryWrite(indexPath, index));

for (const f of fs.readdirSync('artifacts/uxr1-simplification/review')) {
  if (!/^(0[4-9]|1[01])-.*\.html$/.test(f)) continue;
  const p = path.join('artifacts/uxr1-simplification/review', f);
  let c = fs.readFileSync(p, 'utf8');
  c = c
    .replace(
      '<span class="badge pending">PENDING REVIEW</span>',
      '<span class="badge ok">APPROVED · V2</span>',
    )
    .replace(
      '<span class="badge gate">NO IMPLEMENTATION</span>',
      '<span class="badge pending">V2 REFINE</span>',
    );
  console.log(f, tryWrite(p, c));
}

const cssPath = 'artifacts/uxr1-simplification/review/_shared.css';
let css = fs.readFileSync(cssPath, 'utf8');
if (!css.includes('UXR1 V2 palette')) {
  css = css.replace(':root {', ':root {\n  /* UXR1 V2 palette overlay for review chrome */');
  css = css
    .replace('--bg: #f6f7f9;', '--bg: #f8fafc;')
    .replace('--ink: #1a1f2e;', '--ink: #0f2744;')
    .replace('--ink-muted: #5c6578;', '--ink-muted: #64748b;')
    .replace('--stroke: #e4e7ee;', '--stroke: #e2e8f0;')
    .replace('--accent: #1e4d6b;', '--accent: #2563eb;')
    .replace('--accent-soft: #e8f1f6;', '--accent-soft: #eff6ff;')
    .replace('--radius: 12px;', '--radius: 16px;')
    .replace(
      '--shadow: 0 1px 0 rgba(26, 31, 46, 0.04);',
      '--shadow: 0 1px 2px rgba(15, 39, 68, 0.04), 0 6px 20px rgba(15, 39, 68, 0.07);',
    );
}
console.log('css write', tryWrite(cssPath, css));
