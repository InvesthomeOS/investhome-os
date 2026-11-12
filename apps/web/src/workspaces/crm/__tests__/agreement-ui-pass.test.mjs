import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

function source(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
}

test('purchase actions stay in the menu and the cancel button has both states', () => {
  const purchase = source('contact-card/purchase-detail-view.tsx');
  const css = source('contact-card/sales-detail.css');
  assert.match(purchase, /data-testid="purchase-more"/);
  assert.match(purchase, /showMoreMenu/);
  assert.match(purchase, /data-testid="cancel-agreement"/);
  assert.match(purchase, /data-testid="return-pipeline-form"/);
  assert.match(purchase, /data-state=\{cancelPending \|\| !cancelReason\.trim\(\) \? 'disabled' : 'enabled'\}/);
  assert.match(purchase, /numericAmount\(amountEdit\)/);
  assert.match(purchase, /data-testid="purchase-amount-prefix"/);
  assert.match(css, /\.crm-pd-modal__actions \.ih-btn--danger:not\(:disabled\)/);
  assert.match(css, /\.crm-pd-modal__actions \.ih-btn--danger:disabled/);
  assert.match(css, /background: var\(--danger, #dc2626\)/);
  assert.doesNotMatch(purchase, /purchase-edit-open/);
});

test('agreement amounts use one currency helper', () => {
  const money = source('money.ts');
  const stage = readFileSync(new URL('../../../app/workspaces/crm/agreements/_components/agreements-stage.ts', import.meta.url), 'utf8');
  assert.match(money, /USD: '\$'/);
  assert.match(money, /export function formatAgreementAmount/);
  assert.match(money, /export function numericAmount/);
  assert.match(stage, /formatAgreementAmount\(/);
});
