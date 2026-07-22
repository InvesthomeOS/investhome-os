/**
 * Post-capture filesystem verification for G9.5 screenshots.
 * Usage: node artifacts/design-system-g95/verify-pngs.mjs
 */
import { existsSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = dirname(fileURLToPath(import.meta.url));
const expected = [
  '01-overview.png',
  '02-colors-typography.png',
  '03-buttons.png',
  '04-forms.png',
  '05-tables.png',
  '06-filters.png',
  '07-cards.png',
  '08-drawers.png',
  '09-modals.png',
  '10-tabs-nav.png',
  '11-badges.png',
  '12-empty.png',
  '13-loading.png',
  '14-errors.png',
  '15-charts.png',
  '16-responsive.png',
  '17-crm.png',
  '18-investor.png',
  '19-project.png',
  '20-executive.png',
  '21-portal.png',
  '22-turkish.png',
  '23-english.png',
  '24-tablet.png',
];

const rows = expected.map((file) => {
  const abs = join(dir, file);
  const exists = existsSync(abs);
  const bytes = exists ? statSync(abs).size : 0;
  return {
    file,
    abs,
    bytes,
    ok: exists && bytes > 10_000,
  };
});

const listedPng = readdirSync(dir).filter((f) => f.endsWith('.png')).sort();
const pass = rows.every((r) => r.ok) && rows.length === 24 && listedPng.length === 24;

const md = [
  '# G9.5 Screenshot verification',
  '',
  `Directory: \`${dir}\``,
  `Listed PNG count: **${listedPng.length}**`,
  '',
  '| # | Absolute path | Bytes | >10KB |',
  '|---|---------------|------:|:-----:|',
  ...rows.map(
    (r, i) =>
      `| ${i + 1} | \`${r.abs.replace(/\\/g, '/')}\` | ${r.bytes} | ${r.ok ? 'YES' : 'NO'} |`,
  ),
  '',
  `**Result: ${pass ? '24/24 ON DISK (>10KB each)' : 'FAIL — incomplete capture'}**`,
  '',
].join('\n');

writeFileSync(join(dir, 'VERIFIED-SIZES.md'), md);
writeFileSync(
  join(dir, 'verified-sizes.json'),
  JSON.stringify(
    {
      pass,
      expected: 24,
      listedPngCount: listedPng.length,
      okCount: rows.filter((r) => r.ok).length,
      directory: dir,
      rows,
      listedPng,
    },
    null,
    2,
  ),
);

console.log(pass ? 'PASS 24/24' : 'FAIL');
for (const r of rows) {
  console.log(`${r.ok ? 'OK' : 'BAD'}\t${r.bytes}\t${r.abs}`);
}
process.exit(pass ? 0 : 1);
