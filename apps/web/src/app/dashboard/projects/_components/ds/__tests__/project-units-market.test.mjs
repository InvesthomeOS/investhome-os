import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const workspace = readFileSync(
  new URL('../projects-detail-ds-workspace.tsx', import.meta.url),
  'utf8',
);
const styles = readFileSync(new URL('../projects-detail-ds.css', import.meta.url), 'utf8');
const english = readFileSync(new URL('../../../../../../../messages/en.json', import.meta.url), 'utf8');
const turkish = readFileSync(new URL('../../../../../../../messages/tr.json', import.meta.url), 'utf8');

test('project units show the building with the unit number', () => {
  assert.match(workspace, /unit_label/);
  assert.match(workspace, /building_label/);
  assert.match(workspace, /\$\{unit\.building_label\} · \$\{unit\.unit\}/);
});

test('project units filter and count real sales markets', () => {
  assert.match(workspace, /sales_market: market/);
  assert.match(workspace, /total_physical_units/);
  assert.match(workspace, /turkey_allocation/);
  assert.match(workspace, /usa_allocation/);
  assert.match(workspace, /sold_units/);
  assert.match(workspace, /available_for_sale/);
  assert.match(workspace, /project-units-market-/);
  assert.match(styles, /\.proj-detail-ds__unit-stats/);
});

test('sales market labels exist in both locales', () => {
  for (const messages of [english, turkish]) {
    assert.match(messages, /"marketFilter"/);
    assert.match(messages, /"marketUnallocated"/);
    assert.match(messages, /"turkey"/);
    assert.match(messages, /"usa"/);
  }
});
